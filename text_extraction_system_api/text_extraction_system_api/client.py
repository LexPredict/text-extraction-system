import json
import os
import pickle
import tempfile
from contextlib import contextmanager
from typing import Generator, Optional, Dict

import requests

from text_extraction_system_api.dto import PlainTextStructure, TableList, DataFrameTableList, RequestStatus, \
    TaskCancelResult


class TextExtractionSystemWebClient:

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url

    def schedule_data_extraction_task(self,
                                      fn: str,
                                      call_back_url: Optional[str] = None,
                                      call_back_celery_broker: Optional[str] = None,
                                      call_back_celery_queue: Optional[str] = None,
                                      call_back_celery_task_name: Optional[str] = None,
                                      call_back_celery_task_id: Optional[str] = None,
                                      call_back_celery_root_task_id: Optional[str] = None,
                                      call_back_celery_parent_task_id: Optional[str] = None,
                                      call_back_additional_info: Optional[str] = None,
                                      doc_language: Optional[str] = None,
                                      ocr_enable: bool = True,
                                      call_back_celery_version: int = 4,
                                      request_id: str = None,
                                      log_extra: Dict[str, str] = None) -> str:
        resp = requests.post(f'{self.base_url}/api/v1/data_extraction_tasks/',
                             files=dict(file=(os.path.basename(fn), open(fn, 'rb'))),
                             data=dict(call_back_url=call_back_url,
                                       call_back_celery_broker=call_back_celery_broker,
                                       call_back_celery_queue=call_back_celery_queue,
                                       call_back_celery_task_name=call_back_celery_task_name,
                                       call_back_celery_task_id=call_back_celery_task_id,
                                       call_back_celery_root_task_id=call_back_celery_root_task_id,
                                       call_back_celery_parent_task_id=call_back_celery_parent_task_id,
                                       call_back_additional_info=call_back_additional_info,
                                       call_back_celery_version=call_back_celery_version,
                                       doc_language=doc_language,
                                       ocr_enable=ocr_enable,
                                       request_id=request_id,
                                       log_extra_json_key_value=json.dumps(log_extra) if log_extra else None))
        if resp.status_code not in {200, 201}:
            resp.raise_for_status()
        return json.loads(resp.content)

    def get_data_extraction_task_status(self, request_id: str) -> RequestStatus:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/status.json'
        resp = requests.get(url)
        resp.raise_for_status()
        return RequestStatus.from_json(resp.content)

    @contextmanager
    def get_pdf_as_local_file(self, request_id: str) -> Generator[str, None, None]:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/searchable_pdf.pdf'
        _fd, local_filename = tempfile.mkstemp(suffix='.pdf')
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            yield local_filename
        finally:
            os.remove(local_filename)

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
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/extracted_tables.pickle'
        resp = requests.get(url)
        resp.raise_for_status()
        return pickle.loads(resp.content)

    def delete_data_extraction_task_files(self, request_id: str):
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/'
        resp = requests.delete(url)
        resp.raise_for_status()

    def cancel_data_extraction_task(self, request_id: str) -> TaskCancelResult:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/'
        resp = requests.delete(url)
        resp.raise_for_status()
        return TaskCancelResult.from_json(resp.content)
