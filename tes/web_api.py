import json
from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, Form

from .file_storage import webdav_client
from .tasks import process_document

app = FastAPI()


@app.post('/api/v1/text_extraction_tasks/')
async def post_text_extraction_task(file: UploadFile = File(...), call_back_url: str = Form(default=None)):
    request_uid: str = str(uuid4())
    webdav_client.mkdir(f'/{request_uid}')

    metadata = {
        'file_name': file.filename,
        'request_date': datetime.now().isoformat(),
        'call_back_url': call_back_url
    }

    webdav_client.upload_to(json.dumps(metadata, indent=2), f'{request_uid}/metadata.json')
    webdav_client.upload_to(file.file, f'{request_uid}/original_document')
    process_document.apply_async(('some_document_url', file.filename, call_back_url)).get()
    return metadata
