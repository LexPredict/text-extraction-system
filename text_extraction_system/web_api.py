from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response

from text_extraction_system.commons.escape_utils import get_valid_fn
from text_extraction_system.file_storage import get_webdav_client
from text_extraction_system.request_metadata import RequestMetadata, save_request_metadata, load_request_metadata
from text_extraction_system.tasks import process_document

app = FastAPI()


@app.post('/api/v1/data_extraction_tasks/')
async def post_text_extraction_task(file: UploadFile = File(...),
                                    call_back_url: str = Form(default=None),
                                    call_back_celery_broker: str = Form(default=None),
                                    call_back_celery_task_name: str = Form(default=None),
                                    call_back_celery_queue: str = Form(default=None),
                                    call_back_additional_info: str = Form(default=None),
                                    call_back_celery_task_id: str = Form(default=None),
                                    call_back_celery_parent_task_id: str = Form(default=None),
                                    call_back_celery_root_task_id: str = Form(default=None),
                                    call_back_celery_version: int = Form(default=4),
                                    doc_language: str = Form(default='eng')):
    webdav_client = get_webdav_client()
    req = RequestMetadata(original_file_name=file.filename,
                          original_document=get_valid_fn(file.filename),
                          request_id=str(uuid4()),
                          request_date=datetime.now(),
                          call_back_url=call_back_url,
                          doc_language=doc_language,
                          call_back_celery_broker=call_back_celery_broker,
                          call_back_celery_queue=call_back_celery_queue,
                          call_back_celery_task_name=call_back_celery_task_name,
                          call_back_additional_info=call_back_additional_info,
                          call_back_celery_task_id=call_back_celery_task_id,
                          call_back_celery_parent_task_id=call_back_celery_parent_task_id,
                          call_back_celery_root_task_id=call_back_celery_root_task_id,
                          call_back_celery_version=call_back_celery_version)
    webdav_client.mkdir(f'/{req.request_id}')

    save_request_metadata(req)
    webdav_client.upload_to(file.file, f'{req.request_id}/{req.original_document}')
    process_document.apply_async((req.request_id,))
    return req


@app.get('/api/v1/data_extraction_tasks/{request_id}')
async def get_request_metadata(request_id: str):
    req = load_request_metadata(request_id)
    return req


@app.get('/api/v1/data_extraction_tasks/{request_id}/{file_name}')
async def get_request_file(request_id: str, file_name: str):
    req = load_request_metadata(request_id)
    if file_name not in req.to_dict().values():
        raise HTTPException(status_code=404, detail=f'File name is not mentioned in request metadata: {file_name}')
    webdav_client = get_webdav_client()
    resp = webdav_client.execute_request('download', f'/{request_id}/{file_name}')
    return Response(content=resp.content, status_code=resp.status_code)


@app.delete('/api/v1/data_extraction_tasks/{request_id}')
async def delete_request_files(request_id: str):
    get_webdav_client().clean(f'{request_id}')
