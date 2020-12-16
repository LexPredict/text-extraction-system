from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from typing import List, Optional, Dict

from dataclasses_json import dataclass_json, config
from marshmallow import fields

from text_extraction_system.constants import metadata_fn
from text_extraction_system.file_storage import get_webdav_client


@dataclass_json
@dataclass
class RequestMetadata:
    file_name: str
    file_name_in_storage: str
    request_id: str
    request_date: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format='iso')
        )
    )
    call_back_url: str
    pages_for_ocr: Optional[Dict[int, str]] = None


def load_request_metadata(request_id) -> RequestMetadata:
    webdav_client = get_webdav_client()
    buf = BytesIO()
    webdav_client.download_from(buf, f'{request_id}/{metadata_fn}')
    return RequestMetadata.from_json(buf.getvalue())


def save_request_metadata(req: RequestMetadata):
    webdav_client = get_webdav_client()
    webdav_client.upload_to(req.to_json(indent=2), f'{req.request_id}/{metadata_fn}')
