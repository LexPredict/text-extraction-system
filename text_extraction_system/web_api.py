from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, Form

from text_extraction_system.commons.escape_utils import get_valid_fn
from text_extraction_system.file_storage import get_webdav_client
from text_extraction_system.request_metadata import RequestMetadata, save_request_metadata
from text_extraction_system.tasks import process_document

app = FastAPI()


@app.post('/api/v1/text_extraction_tasks/')
async def post_text_extraction_task(file: UploadFile = File(...),
                                    call_back_url: str = Form(default=None),
                                    doc_language: str = 'eng'):
    webdav_client = get_webdav_client()
    req = RequestMetadata(original_file_name=file.filename,
                          original_document=get_valid_fn(file.filename),
                          request_id=str(uuid4()),
                          request_date=datetime.now(),
                          call_back_url=call_back_url,
                          doc_language=doc_language)
    webdav_client.mkdir(f'/{req.request_id}')

    save_request_metadata(req)
    webdav_client.upload_to(file.file, f'{req.request_id}/{req.original_document}')
    process_document.apply_async((req.request_id,))
    return req
