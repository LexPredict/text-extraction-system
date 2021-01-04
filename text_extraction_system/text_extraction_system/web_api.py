from datetime import datetime
from typing import AnyStr
from uuid import uuid4
import json

from fastapi import FastAPI, File, UploadFile, Form, Response
from text_extraction_system_api.dto import TableList, PlainTextStructure, RequestStatus, VersionInfo

from text_extraction_system.commons.escape_utils import get_valid_fn
from text_extraction_system.file_storage import get_webdav_client, WebDavClient
from text_extraction_system.request_metadata import RequestMetadata, save_request_metadata, load_request_metadata
from text_extraction_system.tasks import process_document

app = FastAPI()

@app.post('/api/v1/data_extraction_tasks/', response_model=str)
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
                                    doc_language: str = Form(default='en'),
                                    request_id: str = Form(default=None),
                                    log_extra_json_key_value: str = Form(default=None)):
    webdav_client = get_webdav_client()
    request_id = get_valid_fn(request_id) if request_id else str(uuid4())
    log_extra = json.loads(log_extra_json_key_value) if log_extra_json_key_value else None
    req = RequestMetadata(original_file_name=file.filename,
                          original_document=get_valid_fn(file.filename),
                          request_id=request_id,
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
                          call_back_celery_version=call_back_celery_version,
                          log_extra=log_extra)
    webdav_client.mkdir(f'/{req.request_id}')

    save_request_metadata(req)
    webdav_client.upload_to(file.file, f'{req.request_id}/{req.original_document}')
    process_document.apply_async((req.request_id,))
    return req.request_id


@app.get('/api/v1/data_extraction_tasks/{request_id}/status.json', response_model=RequestStatus)
async def get_request_status(request_id: str):
    req = load_request_metadata(request_id)
    return req.to_request_status().to_dict()


def _proxy_request(webdav_client, request_id: str, fn: str):
    resp: WebDavClient = webdav_client.execute_request('download', f'/{request_id}/{fn}')
    return Response(content=resp.content, status_code=resp.status_code)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/extracted_tables.json',
         response_model=TableList)
async def get_extracted_tables_in_json(request_id: str):
    return _proxy_request(get_webdav_client(), request_id, load_request_metadata(request_id).tables_json_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/extracted_tables.pickle',
         responses={
             200: {
                 'description': 'Pickled DataFrameTableList object.',
                 'content': {'application/octet-stream': {}},
             }
         })
async def get_extracted_tables_as_pickled_dataframe_table_list(request_id: str):
    return _proxy_request(get_webdav_client(), request_id, load_request_metadata(request_id).tables_df_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/extracted_plain_text.txt', response_model=AnyStr)
async def get_extracted_plain_text(request_id: str):
    return _proxy_request(get_webdav_client(), request_id, load_request_metadata(request_id).plain_text_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/plain_text_structure.json',
         response_model=PlainTextStructure)
async def get_extracted_plain_text_structure(request_id: str):
    return _proxy_request(get_webdav_client(), request_id, load_request_metadata(request_id).plain_text_structure_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/searchable_pdf.pdf')
async def get_searchable_pdf(request_id: str):
    return _proxy_request(get_webdav_client(), request_id, load_request_metadata(request_id).pdf_file)


@app.delete('/api/v1/data_extraction_tasks/{request_id}')
async def delete_request_files(request_id: str):
    get_webdav_client().clean(f'{request_id}')


@app.get('/api/v1/version.json', response_model=VersionInfo)
async def get_request_status(request_id: str):
    from text_extraction_system import version
    return VersionInfo(version_number=version.VERSION_NUMBER,
                       git_commit=version.GIT_COMMIT,
                       build_date=version.BUILD_DATE).to_dict()
