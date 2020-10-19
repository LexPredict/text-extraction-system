from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, Form

from .file_storage import webdav_client, get_valid_fn
from .request_metadata import RequestMetadata, metadata_fn
from .tasks import process_document

app = FastAPI()


@app.post('/api/v1/text_extraction_tasks/')
async def post_text_extraction_task(file: UploadFile = File(...), call_back_url: str = Form(default=None)):
    req = RequestMetadata(file_name=file.filename,
                          file_name_in_storage=get_valid_fn(file.filename),
                          request_id=str(uuid4()),
                          request_date=datetime.now(),
                          call_back_url=call_back_url)
    webdav_client.mkdir(f'/{req.request_id}')

    webdav_client.upload_to(req.to_json(indent=2), f'{req.request_id}/{metadata_fn}')
    webdav_client.upload_to(file.file, f'{req.request_id}/{req.file_name_in_storage}')
    process_document.apply_async((req.request_id,)).get()
    return req
