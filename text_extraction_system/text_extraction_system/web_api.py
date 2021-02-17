import json
import os
import sys
from datetime import datetime
from io import BytesIO
from typing import AnyStr, List, Dict
from uuid import uuid4
from zipfile import ZipFile

import pandas
from fastapi import FastAPI, File, UploadFile, Form, Response
from webdav3.exceptions import RemoteResourceNotFound

from text_extraction_system import version
from text_extraction_system.celery_log import HumanReadableTraceBackException
from text_extraction_system.commons.escape_utils import get_valid_fn
from text_extraction_system.constants import task_ids
from text_extraction_system.file_storage import get_webdav_client, WebDavClient
from text_extraction_system.request_metadata import RequestMetadata, RequestCallbackInfo, save_request_metadata, \
    load_request_metadata
from text_extraction_system.tasks import process_document, celery_app, register_task_id, get_request_task_ids
from text_extraction_system_api import dto
from text_extraction_system_api.dto import TableList, PlainTextStructure, RequestStatus, SystemInfo, TaskCancelResult

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
                                    ocr_enable: bool = Form(default=True),
                                    request_id: str = Form(default=None),
                                    log_extra_json_key_value: str = Form(default=None),
                                    convert_to_pdf_timeout_sec: int = Form(default=1800),
                                    pdf_to_images_timeout_sec: int = Form(default=1800)):
    webdav_client = get_webdav_client()
    request_id = get_valid_fn(request_id) if request_id else str(uuid4())
    log_extra = json.loads(log_extra_json_key_value) if log_extra_json_key_value else None
    req = RequestMetadata(original_file_name=file.filename,
                          original_document=get_valid_fn(file.filename),
                          request_id=request_id,
                          request_date=datetime.now(),
                          doc_language=doc_language,
                          ocr_enable=ocr_enable,
                          convert_to_pdf_timeout_sec=convert_to_pdf_timeout_sec,
                          pdf_to_images_timeout_sec=pdf_to_images_timeout_sec,
                          request_callback_info=RequestCallbackInfo(
                              request_id=request_id,
                              original_file_name=file.filename,
                              call_back_url=call_back_url,
                              call_back_celery_broker=call_back_celery_broker,
                              call_back_celery_queue=call_back_celery_queue,
                              call_back_celery_task_name=call_back_celery_task_name,
                              call_back_additional_info=call_back_additional_info,
                              call_back_celery_task_id=call_back_celery_task_id,
                              call_back_celery_parent_task_id=call_back_celery_parent_task_id,
                              call_back_celery_root_task_id=call_back_celery_root_task_id,
                              call_back_celery_version=call_back_celery_version,
                              log_extra=log_extra))
    webdav_client.mkdir(f'/{req.request_id}')

    save_request_metadata(req)
    webdav_client.upload_to(file.file, f'{req.request_id}/{req.original_document}')
    async_task = process_document.apply_async((req.request_id, req.request_callback_info))

    webdav_client.mkdir(f'{req.request_id}/{task_ids}')
    register_task_id(webdav_client, req.request_id, async_task.id)

    return req.request_id


@app.delete('/api/v1/data_extraction_tasks/{request_id}/', response_model=TaskCancelResult)
async def purge_text_extraction_task(request_id: str):
    problems = dict()
    success = list()
    celery_task_ids: List[str] = get_request_task_ids(get_webdav_client(), request_id)
    for task_id in celery_task_ids:
        try:
            celery_app.control.revoke(task_id, terminate=True)
            success.append(task_id)
        except Exception as ex:
            problems[task_id] = HumanReadableTraceBackException \
                .from_exception(ex) \
                .human_readable_format()
    try:
        get_webdav_client().clean(f'{request_id}/')
    except RemoteResourceNotFound:
        problems[''] = f'Request "{request_id}" is not instantiated on WebDAV'

    return TaskCancelResult(request_id=request_id,
                            task_ids=celery_task_ids,
                            successfully_revoked=success,
                            problems=problems).to_dict()


@app.get('/api/v1/data_extraction_tasks/{request_id}/status.json', response_model=RequestStatus)
async def get_request_status(request_id: str):
    req = load_request_metadata(request_id)
    return req.to_request_status().to_dict()


def _proxy_request(webdav_client, request_id: str, fn: str, headers: Dict[str, str] = None):
    resp: WebDavClient = webdav_client.execute_request('download', f'/{request_id}/{fn}')
    return Response(content=resp.content, status_code=resp.status_code, headers=headers)


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
    return _proxy_request(get_webdav_client(),
                          request_id,
                          load_request_metadata(request_id).plain_text_file,
                          headers={'Content-Type': 'text/plain; charset=utf-8'})


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/plain_text_structure.json',
         response_model=PlainTextStructure)
async def get_extracted_plain_text_structure(request_id: str):
    return _proxy_request(get_webdav_client(), request_id, load_request_metadata(request_id).plain_text_structure_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/searchable_pdf.pdf')
async def get_searchable_pdf(request_id: str):
    return _proxy_request(get_webdav_client(), request_id, load_request_metadata(request_id).pdf_file)


@app.delete('/api/v1/data_extraction_tasks/{request_id}/results/')
async def delete_request_files(request_id: str):
    get_webdav_client().clean(f'{request_id}/')


@app.get('/api/v1/system_info.json', response_model=SystemInfo)
async def get_system_info():
    return SystemInfo(version_number=version.VERSION_NUMBER,
                      git_branch=version.GIT_BRANCH,
                      git_commit=version.GIT_COMMIT,
                      lexnlp_git_branch=version.LEXNLP_GIT_BRANCH,
                      lexnlp_git_commit=version.LEXNLP_GIT_COMMIT,
                      build_date=version.BUILD_DATE,
                      python_version=sys.version,
                      pandas_version=pandas.__version__).to_dict()


@app.get('/api/v1/download_python_api_client')
async def download_python_api_client_and_dtos():
    folder_exclude = {'lexpredict_text_extraction_system_api.egg-info', '__pycache__'}
    file_exclude = {'.gitignore'}

    dir_name = os.path.dirname(os.path.dirname(os.path.abspath(dto.__file__)))

    b = BytesIO()
    fn = f'text_extraction_system_python_api_{version.VERSION_NUMBER}.zip'
    with ZipFile(b, 'w') as zip_obj:
        for root, dirs, files in os.walk(dir_name):
            if os.path.basename(root) in folder_exclude:
                continue
            for file in files:
                if os.path.basename(file) in file_exclude:
                    continue
                zip_obj.write(os.path.join(root, file),
                              os.path.relpath(os.path.join(root, file), os.path.join(dir_name, '..')))

    return Response(b.getvalue(), status_code=200, media_type='application/x-zip-compressed', headers={
        'Content-Disposition': f'attachment; filename={fn}'
    })
