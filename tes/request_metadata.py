from dataclasses import dataclass, field
from datetime import datetime

from dataclasses_json import dataclass_json, config
from marshmallow import fields

metadata_fn = 'metadata.json'
results_fn = 'results.zip'


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
