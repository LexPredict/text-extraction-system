from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from typing import Optional, Dict

from dataclasses_json import dataclass_json, config
from marshmallow import fields
from text_extraction_system_api.dto import RequestStatus

from text_extraction_system.constants import metadata_fn
from text_extraction_system.file_storage import get_webdav_client

STATUS_PENDING = 'PENDING'
STATUS_DONE = 'DONE'


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
    call_back_url: Optional[str] = None
    call_back_celery_broker: Optional[str] = None
    call_back_celery_queue: Optional[str] = None
    call_back_celery_task_name: Optional[str] = None
    call_back_celery_task_id: Optional[str] = None,
    call_back_celery_root_task_id: Optional[str] = None,
    call_back_celery_parent_task_id: Optional[str] = None
    call_back_additional_info: Optional[str] = None
    call_back_celery_version: int = 4

    def to_request_status(self) -> RequestStatus:
        return RequestStatus(
            request_id=self.request_id,
            original_file_name=self.original_file_name,
            status=self.status,
            converted_to_pdf=self.converted_to_pdf is not None,
            searchable_pdf_created=self.ocred_pdf is not None,
            pdf_pages_ocred=sorted(list(self.pages_for_ocr.keys())) if self.pages_for_ocr else None,
            tables_extracted=self.tables_json_file is not None,
            plain_text_extracted=self.plain_text_file is not None,
            plain_text_structure_extracted=self.plain_text_structure_file is not None,
            additional_info=self.call_back_additional_info
        )


def load_request_metadata(request_id) -> RequestMetadata:
    webdav_client = get_webdav_client()
    buf = BytesIO()
    webdav_client.download_from(buf, f'{request_id}/{metadata_fn}')
    return RequestMetadata.from_json(buf.getvalue())


def save_request_metadata(req: RequestMetadata):
    webdav_client = get_webdav_client()
    webdav_client.upload_to(req.to_json(indent=2).encode('utf-8'), f'{req.request_id}/{metadata_fn}')
