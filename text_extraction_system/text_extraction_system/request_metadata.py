from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from typing import Optional, Dict, List

from dataclasses_json import dataclass_json, config
from marshmallow import fields
from webdav3.exceptions import RemoteResourceNotFound, RemoteParentNotFound

from text_extraction_system.constants import metadata_fn
from text_extraction_system.file_storage import get_webdav_client
from text_extraction_system_api.dto import RequestStatus, STATUS_PENDING


@dataclass_json
@dataclass
class RequestCallbackInfo:
    request_id: str
    original_file_name: str
    call_back_url: Optional[str] = None
    call_back_celery_broker: Optional[str] = None
    call_back_celery_queue: Optional[str] = None
    call_back_celery_task_name: Optional[str] = None
    call_back_celery_task_id: Optional[str] = None
    call_back_celery_root_task_id: Optional[str] = None
    call_back_celery_parent_task_id: Optional[str] = None
    call_back_additional_info: Optional[str] = None
    call_back_celery_version: int = 4
    log_extra: Optional[Dict[str, str]] = None


@dataclass_json
@dataclass
class RequestMetadata:
    request_id: str
    request_date: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format='iso')
        )
    )
    original_file_name: str
    original_document: str

    request_callback_info: RequestCallbackInfo

    status: str = STATUS_PENDING
    converted_to_pdf: Optional[str] = None
    ocred_pdf: Optional[str] = None
    pdf_file: Optional[str] = None
    tika_xhtml_file: Optional[str] = None
    plain_text_file: Optional[str] = None
    plain_text_structure_file: Optional[str] = None
    tables_json_file: Optional[str] = None
    tables_df_file: Optional[str] = None
    doc_language: Optional[str] = None
    pages_for_ocr: Optional[Dict[int, str]] = None
    error_message: Optional[str] = None

    def append_error(self, problem: str, exc: Exception):
        error_message: List[str] = list()
        if self.error_message:
            error_message.append(self.error_message)

        if exc:
            from celery_log import HumanReadableTraceBackException
            error_message.append(HumanReadableTraceBackException.from_exception(exc).human_readable_format())
        self.error_message = '\n'.join(error_message)

    def to_request_status(self) -> RequestStatus:
        return RequestStatus(
            request_id=self.request_id,
            original_file_name=self.original_file_name,
            status=self.status,
            error_message=self.error_message,
            converted_to_pdf=self.converted_to_pdf is not None,
            searchable_pdf_created=self.ocred_pdf is not None,
            pdf_pages_ocred=sorted(list(self.pages_for_ocr.keys())) if self.pages_for_ocr else None,
            tables_extracted=self.tables_json_file is not None,
            plain_text_extracted=self.plain_text_file is not None,
            plain_text_structure_extracted=self.plain_text_structure_file is not None,
            additional_info=self.request_callback_info.call_back_additional_info
        )


def load_request_metadata(request_id) -> Optional[RequestMetadata]:
    try:
        webdav_client = get_webdav_client()
        buf = BytesIO()
        webdav_client.download_from(buf, f'{request_id}/{metadata_fn}')
        return RequestMetadata.from_json(buf.getvalue())
    except (RemoteParentNotFound, RemoteResourceNotFound):
        return None


def save_request_metadata(req: RequestMetadata):
    webdav_client = get_webdav_client()
    webdav_client.upload_to(req.to_json(indent=2).encode('utf-8'), f'{req.request_id}/{metadata_fn}')
