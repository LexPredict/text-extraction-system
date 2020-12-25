import json
import os
import pickle
import tempfile
from typing import Generator, Any, List

import requests

from text_extraction_system.api.dto import PlainTextStructure, TableList, DataFrameTableList


class TextExtractionSystemWebClient:

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url

    def get_pdf_as_local_file(self, request_id: str) -> Generator[str, None, None]:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/searchable_pdf.pdf'
        return self._get_as_local_fn(url, '.pdf')

    def get_plain_text(self, request_id: str) -> str:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/extracted_plain_text.txt'
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.text

    def get_plain_text_structure(self, request_id: str) -> PlainTextStructure:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/plain_text_structure.json'
        resp = requests.get(url)
        resp.raise_for_status()
        return PlainTextStructure.from_json(resp.content)

    def get_tables_json(self, request_id: str) -> TableList:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/extracted_tables.json'
        resp = requests.get(url)
        resp.raise_for_status()
        return TableList.from_json(resp.content)

    def get_tables_df(self, request_id: str) -> DataFrameTableList:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/result/extracted_tables.pickle'
        resp = requests.get(url)
        resp.raise_for_status()
        return pickle.loads(resp.content)

    def delete_request_files(self, request_id: str):
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}'
        resp = requests.delete(url)
        resp.raise_for_status()

    def _get_as_local_fn(self, url: str, ext: str) -> Generator[str, None, None]:
        _fd, local_filename = tempfile.mkstemp(suffix=ext)
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            yield local_filename
        finally:
            os.remove(local_filename)
