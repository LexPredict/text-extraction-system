import json
import os
import pickle
import tempfile
from contextlib import contextmanager
from typing import Generator, Optional, Dict

import msgpack
import requests

from text_extraction_system_api.dto import PlainTextStructure, MarkupPerSymbol, TextPlusMarkup, \
    TableList, DataFrameTableList, RequestStatus, TaskCancelResult, \
    PlainTextPage, PlainTextSentence, PlainTextParagraph, PlainTextSection, Table


class Constants:
    output_format_msgpack = 'msgpack'
    output_format_json = 'json'


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
                                      convert_to_pdf_timeout_sec: int = 1800,
                                      pdf_to_images_timeout_sec: int = 1800,
                                      ocr_enable: bool = True,
                                      call_back_celery_version: int = 4,
                                      request_id: str = None,
                                      log_extra: Dict[str, str] = None,
                                      glyph_enhancing: bool = False,
                                      output_format: str = Constants.output_format_msgpack) -> str:
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
                                       convert_to_pdf_timeout_sec=convert_to_pdf_timeout_sec,
                                       pdf_to_images_timeout_sec=pdf_to_images_timeout_sec,
                                       doc_language=doc_language,
                                       ocr_enable=ocr_enable,
                                       request_id=request_id,
                                       log_extra_json_key_value=json.dumps(log_extra) if log_extra else None,
                                       glyph_enhancing=glyph_enhancing,
                                       output_format=output_format))
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

    def get_text_structure_json(self, request_id: str) -> PlainTextStructure:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/document_structure.json'
        resp = requests.get(url)
        resp.raise_for_status()
        return PlainTextStructure.from_json(resp.content)

    def get_text_structure_msgpack(self, request_id: str) -> PlainTextStructure:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/document_structure.msgpack'
        resp = requests.get(url)
        resp.raise_for_status()
        return self._unpack_msgpack_text_structure(resp.content)

    def get_text_markup_json(self, request_id: str) -> MarkupPerSymbol:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/document_markup.json'
        resp = requests.get(url)
        resp.raise_for_status()
        return MarkupPerSymbol.from_json(resp.content)

    def get_text_markup_msgpack(self, request_id: str) -> MarkupPerSymbol:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/document_markup.msgpack'
        resp = requests.get(url)
        resp.raise_for_status()
        data = msgpack.unpackb(resp.content, raw=False)
        return MarkupPerSymbol(**data)

    def get_text_markup_msgpack_raw(self, request_id: str) -> Optional[bytes]:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/document_markup.msgpack'
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.content

    def get_tables_json(self, request_id: str) -> TableList:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/extracted_tables.json'
        resp = requests.get(url)
        resp.raise_for_status()
        return TableList.from_json(resp.content)

    def get_tables_msgpack(self, request_id: str) -> TableList:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/extracted_tables.pickle'
        resp = requests.get(url)
        resp.raise_for_status()
        data = msgpack.unpackb(resp.content, raw=False)
        tab_lst = TableList(tables=[])
        for table in data:
            tab_lst.tables.append(Table(**table))
        return tab_list

    def delete_data_extraction_task_files(self, request_id: str):
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/'
        resp = requests.delete(url)
        resp.raise_for_status()

    def cancel_data_extraction_task(self, request_id: str) -> TaskCancelResult:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/'
        resp = requests.delete(url)
        resp.raise_for_status()
        return TaskCancelResult.from_json(resp.content)

    @classmethod
    def _unpack_msgpack_text_structure(cls, data: Optional[bytes]) -> Optional[PlainTextStructure]:
        if not data:
            return None
        shallow_structure = msgpack.unpackb(data, raw=False)
        ps = PlainTextStructure(title=shallow_structure.get('title'),
                                language=shallow_structure.get('language'),
                                pages=[], sentences=[], paragraphs=[], sections=[])
        ps.pages = [PlainTextPage(**p) for p in shallow_structure.get('pages', [])]
        ps.sentences = [PlainTextSentence(**p) for p in shallow_structure.get('sentences', [])]
        ps.paragraphs = [PlainTextParagraph(**p) for p in shallow_structure.get('paragraphs', [])]
        ps.sections = [PlainTextSection(**p) for p in shallow_structure.get('sections', [])]
        return ps
