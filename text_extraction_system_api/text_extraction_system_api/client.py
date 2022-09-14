import json
import os
import tempfile
from io import BufferedReader, BytesIO
from contextlib import contextmanager
from typing import Generator, Optional, Dict, List, Union

import msgpack
import requests
from requests.models import Response, HTTPError
from requests.auth import HTTPBasicAuth

from text_extraction_system_api.dto import PlainTextStructure, PDFCoordinates, TableList, RequestStatus, \
    PlainTextPage, PlainTextSentence, PlainTextParagraph, PlainTextSection, PlainTableOfContentsRecord, \
    Table, OutputFormat, TaskCancelResult, TableParser


class TextExtractionSystemWebClient:

    def __init__(
        self,
        base_url: str,
        username: str = None,
        password: str = None,
    ) -> None:
        super().__init__()
        self.base_url: str = base_url
        self.auth: HTTPBasicAuth = HTTPBasicAuth(username, password)

    @staticmethod
    def raise_for_status(resp: Response):
        try:
            resp.raise_for_status()
        except HTTPError as e:
            message = '\n'.join([str(a) for a in e.args])
            body_str = str(resp.request.body)
            resp_body = str(resp.text)
            if len(body_str) > 2048:
                body_str = body_str[:2048] + '...'
            message += f'\nRequest url:\n{resp.request.url}' \
                       f'\nRequest headers:\n{resp.request.headers}' \
                       f'\nRequest body:\n{body_str}\n' \
                       f'\n' \
                       f'\nResponse body:\n{resp_body}\n'
            raise HTTPError(message, response=resp)

    def schedule_data_extraction_task_from_bytes(
        self,
        file_name: str,
        file_bytes: Union[bytes, BytesIO, BufferedReader],
        call_back_url: Optional[str] = None,
        call_back_celery_broker: Optional[str] = None,
        call_back_celery_queue: Optional[str] = None,
        call_back_celery_task_name: Optional[str] = None,
        call_back_celery_task_id: Optional[str] = None,
        call_back_celery_root_task_id: Optional[str] = None,
        call_back_celery_parent_task_id: Optional[str] = None,
        call_back_additional_info: Optional[str] = None,
        estimation_call_back_url: Optional[str] = None,
        progress_call_back_url: Optional[str] = None,
        doc_language: Optional[str] = None,
        convert_to_pdf_timeout_sec: int = 1800,
        pdf_to_images_timeout_sec: int = 1800,
        ocr_enable: bool = True,
        table_extraction_enable: bool = True,
        deskew_enable: bool = True,
        char_coords_debug_enable: bool = False,
        call_back_celery_version: int = 4,
        request_id: str = None,
        log_extra: Dict[str, str] = None,
        glyph_enhancing: bool = False,
        remove_non_printable: bool = False,
        output_format: OutputFormat = OutputFormat.json,
        read_sections_from_toc: bool = True,
        page_ocr_timeout_sec: int = 60,
        remove_ocr_layer: bool = False,
        detect_orientation_tesseract: bool = False
    ) -> str:
        """
        Takes bytes, BytesIO, or a BufferedReader in as input and
        schedules a data extraction task.
        """
        if isinstance(file_bytes, bytes):
            buffered_reader: BufferedReader = BufferedReader(BytesIO(file_bytes))
        elif isinstance(file_bytes, BytesIO):
            buffered_reader: BufferedReader = BufferedReader(file_bytes)
        elif isinstance(file_bytes, BufferedReader):
            buffered_reader: BufferedReader = file_bytes
        else:
            raise TypeError(
                'Argument `file_bytes` must be one of'
                'bytes, BytesIO, or BufferedReader.'
                f' Received: {type(file_bytes)}.'
            )
        resp: Response = requests.post(
            url=f'{self.base_url}/api/v1/data_extraction_tasks/',
            auth=self.auth,
            files={'file': (os.path.basename(file_name), buffered_reader)},
            data={
                'call_back_url': call_back_url,
                'call_back_celery_broker': call_back_celery_broker,
                'call_back_celery_queue': call_back_celery_queue,
                'call_back_celery_task_name': call_back_celery_task_name,
                'call_back_celery_task_id': call_back_celery_task_id,
                'call_back_celery_root_task_id': call_back_celery_root_task_id,
                'call_back_celery_parent_task_id': call_back_celery_parent_task_id,
                'call_back_additional_info': call_back_additional_info,
                'call_back_celery_version': call_back_celery_version,
                'estimation_call_back_url': estimation_call_back_url,
                'progress_call_back_url': progress_call_back_url,
                'convert_to_pdf_timeout_sec': convert_to_pdf_timeout_sec,
                'pdf_to_images_timeout_sec': pdf_to_images_timeout_sec,
                'doc_language': doc_language,
                'ocr_enable': ocr_enable,
                'table_extraction_enable': table_extraction_enable,
                'deskew_enable': deskew_enable,
                'char_coords_debug_enable': char_coords_debug_enable,
                'request_id': request_id,
                'log_extra_json_key_value': json.dumps(log_extra) if log_extra else None,
                'glyph_enhancing': glyph_enhancing,
                'remove_non_printable': remove_non_printable,
                'output_format': output_format.value,
                'read_sections_from_toc': read_sections_from_toc,
                'page_ocr_timeout_sec': page_ocr_timeout_sec,
                'remove_ocr_layer': remove_ocr_layer,
                'detect_orientation_tesseract': detect_orientation_tesseract
            }
        )
        if resp.status_code not in {200, 201}:
            self.raise_for_status(resp)
        return json.loads(resp.content)

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
                                      estimation_call_back_url: Optional[str] = None,
                                      progress_call_back_url: Optional[str] = None,
                                      doc_language: Optional[str] = None,
                                      convert_to_pdf_timeout_sec: int = 1800,
                                      pdf_to_images_timeout_sec: int = 1800,
                                      ocr_enable: bool = True,
                                      table_extraction_enable: bool = True,
                                      deskew_enable: bool = True,
                                      char_coords_debug_enable: bool = False,
                                      call_back_celery_version: int = 4,
                                      request_id: str = None,
                                      log_extra: Dict[str, str] = None,
                                      glyph_enhancing: bool = False,
                                      remove_non_printable: bool = False,
                                      output_format: OutputFormat = OutputFormat.json,
                                      read_sections_from_toc: bool = True,
                                      table_parser: TableParser = TableParser.lattice,
                                      page_ocr_timeout_sec: int = 60,
                                      remove_ocr_layer: bool = False,
                                      detect_orientation_tesseract: bool = False) -> str:
        resp = requests.post(f'{self.base_url}/api/v1/data_extraction_tasks/',
                             auth=self.auth,
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
                                       estimation_call_back_url=estimation_call_back_url,
                                       progress_call_back_url=progress_call_back_url,
                                       convert_to_pdf_timeout_sec=convert_to_pdf_timeout_sec,
                                       pdf_to_images_timeout_sec=pdf_to_images_timeout_sec,
                                       doc_language=doc_language,
                                       ocr_enable=ocr_enable,
                                       table_extraction_enable=table_extraction_enable,
                                       deskew_enable=deskew_enable,
                                       char_coords_debug_enable=char_coords_debug_enable,
                                       request_id=request_id,
                                       log_extra_json_key_value=json.dumps(log_extra) if log_extra else None,
                                       glyph_enhancing=glyph_enhancing,
                                       remove_non_printable=remove_non_printable,
                                       output_format=output_format.value,
                                       read_sections_from_toc=read_sections_from_toc,
                                       table_parser=table_parser.value,
                                       page_ocr_timeout_sec=page_ocr_timeout_sec,
                                       remove_ocr_layer=remove_ocr_layer,
                                       detect_orientation_tesseract=detect_orientation_tesseract))
        if resp.status_code not in {200, 201}:
            self.raise_for_status(resp)
        return json.loads(resp.content)

    def get_data_extraction_task_status(self, request_id: str) -> RequestStatus:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/status.json'
        resp = requests.get(url, auth=self.auth)
        self.raise_for_status(resp)
        return RequestStatus.from_json(resp.content)

    @contextmanager
    def get_pdf_as_local_file(self, request_id: str) -> Generator[str, None, None]:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/searchable_pdf.pdf'
        _fd, local_filename = tempfile.mkstemp(suffix='.pdf')
        try:
            with requests.get(url, stream=True, auth=self.auth) as r:
                self.raise_for_status(r)
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            yield local_filename
        finally:
            os.remove(local_filename)

    def get_plain_text(self, request_id: str) -> str:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/extracted_plain_text.txt'
        resp = requests.get(url, auth=self.auth)
        self.raise_for_status(resp)
        return resp.text

    def get_extracted_text_structure_as_json(self, request_id: str) -> PlainTextStructure:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/document_structure.json'
        resp = requests.get(url, auth=self.auth)
        self.raise_for_status(resp)
        return PlainTextStructure.from_json(resp.content)

    def get_extracted_text_structure_as_msgpack(self, request_id: str) -> PlainTextStructure:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/document_structure.msgpack'
        resp = requests.get(url, auth=self.auth)
        self.raise_for_status(resp)
        return self._unpack_msgpack_text_structure(resp.content)

    def get_extracted_pdf_coordinates_as_json(self, request_id: str) -> PDFCoordinates:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/pdf_coordinates.json'
        resp = requests.get(url, auth=self.auth)
        self.raise_for_status(resp)
        return PDFCoordinates.from_json(resp.content)

    def get_extracted_pdf_coordinates_as_msgpack(self, request_id: str) -> PDFCoordinates:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/pdf_coordinates.msgpack'
        resp = requests.get(url, auth=self.auth)
        self.raise_for_status(resp)
        data = msgpack.unpackb(resp.content, raw=False)
        return PDFCoordinates(**data)

    def get_extracted_pdf_coordinates_as_msgpack_raw(self, request_id: str) -> Optional[bytes]:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/pdf_coordinates.msgpack'
        resp = requests.get(url, auth=self.auth)
        self.raise_for_status(resp)
        return resp.content

    def get_extracted_tables_as_json(self, request_id: str) -> TableList:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/extracted_tables.json'
        resp = requests.get(url, auth=self.auth)
        self.raise_for_status(resp)
        return TableList.from_json(resp.content)

    def get_extracted_tables_as_msgpack(self, request_id: str) -> TableList:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/extracted_tables.msgpack'
        resp = requests.get(url, auth=self.auth)
        self.raise_for_status(resp)
        data = msgpack.unpackb(resp.content, raw=False)
        tab_list: List[Table] = list()
        for table in data['tables']:
            tab_list.append(Table(**table))
        return TableList(tables=tab_list)

    def delete_data_extraction_task_files(self, request_id: str):
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/results/'
        resp = requests.delete(url, auth=self.auth)
        self.raise_for_status(resp)

    def purge_data_extraction_task(self, request_id: str) -> TaskCancelResult:
        url = f'{self.base_url}/api/v1/data_extraction_tasks/{request_id}/'
        resp = requests.delete(url, auth=self.auth)
        self.raise_for_status(resp)
        return TaskCancelResult.from_json(resp.content)

    @classmethod
    def _unpack_msgpack_text_structure(cls, data: Optional[bytes]) -> Optional[PlainTextStructure]:
        if not data:
            return None
        shallow_structure = msgpack.unpackb(data, raw=False)
        ps = PlainTextStructure(title=shallow_structure.get('title'),
                                language=shallow_structure.get('language'),
                                pages=[], sentences=[], paragraphs=[], sections=[], table_of_contents=[])
        ps.pages = [PlainTextPage(**p) for p in shallow_structure.get('pages', [])]
        ps.sentences = [PlainTextSentence(**p) for p in shallow_structure.get('sentences', [])]
        ps.paragraphs = [PlainTextParagraph(**p) for p in shallow_structure.get('paragraphs', [])]
        ps.sections = [PlainTextSection(**p) for p in shallow_structure.get('sections', [])]
        ps.table_of_contents = [PlainTableOfContentsRecord(**p) for p
                                in shallow_structure.get('table_of_contents', [])]
        return ps

    def extract_plain_text_from_document(self,
                                         fn: str,
                                         doc_language: Optional[str] = None,
                                         convert_to_pdf_timeout_sec: int = 1800,
                                         pdf_to_images_timeout_sec: int = 1800,
                                         full_extract_timeout_sec: int = 300,
                                         glyph_enhancing: bool = False,
                                         char_coords_debug_enable: bool = False,
                                         output_format: OutputFormat = OutputFormat.json) -> str:
        resp = requests.post(f'{self.base_url}/api/v1/extract/plain_text/',
                             auth=self.auth,
                             files=dict(file=(os.path.basename(fn), open(fn, 'rb'))),
                             data=dict(convert_to_pdf_timeout_sec=convert_to_pdf_timeout_sec,
                                       pdf_to_images_timeout_sec=pdf_to_images_timeout_sec,
                                       full_extract_timeout_sec=full_extract_timeout_sec,
                                       doc_language=doc_language,
                                       glyph_enhancing=glyph_enhancing,
                                       char_coords_debug_enable=char_coords_debug_enable,
                                       output_format=output_format.value))
        if resp.status_code not in {200, 201}:
            self.raise_for_status(resp)
        return resp.text

    @contextmanager
    def extract_text_from_document_and_generate_searchable_pdf_as_local_file(
            self, fn: str,
            doc_language: Optional[str] = None,
            convert_to_pdf_timeout_sec: int = 1800,
            pdf_to_images_timeout_sec: int = 1800,
            full_extract_timeout_sec: int = 300,
            glyph_enhancing: bool = False,
            char_coords_debug_enable: bool = False,
            output_format: OutputFormat = OutputFormat.json) -> Generator[str, None, None]:
        _fd, local_filename = tempfile.mkstemp(suffix='.pdf')
        try:
            with requests.post(f'{self.base_url}/api/v1/extract/searchable_pdf/',
                               auth=self.auth,
                               files=dict(file=(os.path.basename(fn), open(fn, 'rb'))),
                               data=dict(convert_to_pdf_timeout_sec=convert_to_pdf_timeout_sec,
                                         pdf_to_images_timeout_sec=pdf_to_images_timeout_sec,
                                         full_extract_timeout_sec=full_extract_timeout_sec,
                                         doc_language=doc_language,
                                         glyph_enhancing=glyph_enhancing,
                                         char_coords_debug_enable=char_coords_debug_enable,
                                         output_format=output_format.value), stream=True) as r:
                if r.status_code not in {200, 201}:
                    self.raise_for_status(r)
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            yield local_filename
        finally:
            os.remove(local_filename)

    @contextmanager
    def extract_all_data_from_document(
            self, fn: str,
            doc_language: Optional[str] = None,
            convert_to_pdf_timeout_sec: int = 1800,
            pdf_to_images_timeout_sec: int = 1800,
            full_extract_timeout_sec: int = 300,
            glyph_enhancing: bool = False,
            char_coords_debug_enable: bool = False,
            output_format: OutputFormat = OutputFormat.json) -> Generator[str, None, None]:
        _fd, local_filename = tempfile.mkstemp(suffix='.zip')
        try:
            with requests.post(f'{self.base_url}/api/v1/extract/text_and_structure/',
                               auth=self.auth,
                               files=dict(file=(os.path.basename(fn), open(fn, 'rb'))),
                               data=dict(convert_to_pdf_timeout_sec=convert_to_pdf_timeout_sec,
                                         pdf_to_images_timeout_sec=pdf_to_images_timeout_sec,
                                         full_extract_timeout_sec=full_extract_timeout_sec,
                                         doc_language=doc_language,
                                         glyph_enhancing=glyph_enhancing,
                                         char_coords_debug_enable=char_coords_debug_enable,
                                         output_format=output_format.value), stream=True) as r:
                if r.status_code not in {200, 201}:
                    self.raise_for_status(r)
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            yield local_filename
        finally:
            os.remove(local_filename)
