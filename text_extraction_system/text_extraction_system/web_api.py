import io
import json
import os
import sys
import time
import zipfile
from datetime import datetime
from io import BytesIO
from shutil import rmtree
from tempfile import mkdtemp
from typing import AnyStr, List, Dict, Any, Callable, Optional
from uuid import uuid4
from zipfile import ZipFile

import pandas
from fastapi import FastAPI, File, UploadFile, Form, Response, APIRouter
from fastapi.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.staticfiles import StaticFiles
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from starlette.templating import Jinja2Templates
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
from text_extraction_system_api.dto import OutputFormat, TableList, PlainTextStructure, RequestStatus, \
    RequestStatuses, SystemInfo, TaskCancelResult, PDFCoordinates, STATUS_DONE, STATUS_FAILURE, UserRequestsSummary, \
    STATUS_PENDING, UserRequestsQuery, TableParser, RequestEstimate, RequestProgress

app = FastAPI()

apiRouter = APIRouter()

app.mount("/static", StaticFiles(directory="text_extraction_system/templates"), name="static")

app.include_router(
    apiRouter,
    prefix="/api",
)

templates = Jinja2Templates(directory="text_extraction_system/templates")


@app.get("/", tags=['Others'])
async def redirect_to_swagger_ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("", tags=['Others'])
async def serve_spa_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/page-{rest_of_path:path}")
async def serve_spa_rest(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post('/api/v1/data_extraction_tasks/', response_model=str, tags=["Asynchronous Data Extraction"])
async def post_data_extraction_task(file: UploadFile = File(...),
                                    call_back_url: str = Form(default=None),
                                    call_back_celery_broker: str = Form(default=None),
                                    call_back_celery_task_name: str = Form(default=None),
                                    call_back_celery_queue: str = Form(default=None),
                                    call_back_additional_info: str = Form(default=None),
                                    call_back_celery_task_id: str = Form(default=None),
                                    call_back_celery_parent_task_id: str = Form(default=None),
                                    call_back_celery_root_task_id: str = Form(default=None),
                                    call_back_celery_version: int = Form(default=4),
                                    estimation_call_back_url: str = Form(default=None),
                                    progress_call_back_url: str = Form(default=None),
                                    doc_language: str = Form(default=''),
                                    ocr_enable: bool = Form(default=True),
                                    table_extraction_enable: bool = Form(default=True),
                                    deskew_enable: bool = Form(default=True),
                                    char_coords_debug_enable: bool = Form(default=False),
                                    request_id: str = Form(default=None),
                                    log_extra_json_key_value: str = Form(default=None),
                                    convert_to_pdf_timeout_sec: int = Form(default=1800),
                                    pdf_to_images_timeout_sec: int = Form(default=1800),
                                    output_format: OutputFormat = Form(default=OutputFormat.json),
                                    read_sections_from_toc: bool = Form(default=True),
                                    table_parser: TableParser = Form(default=TableParser.lattice),
                                    page_ocr_timeout_sec: int = Form(default=60),
                                    remove_ocr_layer: bool = Form(default=False),
                                    detect_orientation_tesseract: bool = Form(default=False),):
    webdav_client = get_webdav_client()
    request_id = get_valid_fn(request_id) if request_id else str(uuid4())
    log_extra = json.loads(log_extra_json_key_value) if log_extra_json_key_value else None
    req = RequestMetadata(original_file_name=file.filename,
                          original_document=get_valid_fn(file.filename),
                          request_id=request_id,
                          request_date=datetime.now(),
                          doc_language=doc_language,
                          ocr_enable=ocr_enable,
                          table_extraction_enable=table_extraction_enable,
                          deskew_enable=deskew_enable,
                          char_coords_debug_enable=char_coords_debug_enable,
                          output_format=output_format,
                          convert_to_pdf_timeout_sec=convert_to_pdf_timeout_sec,
                          pdf_to_images_timeout_sec=pdf_to_images_timeout_sec,
                          read_sections_from_toc=read_sections_from_toc,
                          table_parser=table_parser,
                          page_ocr_timeout_sec=page_ocr_timeout_sec,
                          remove_ocr_layer=remove_ocr_layer,
                          detect_orientation_tesseract=detect_orientation_tesseract,
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
                              call_back_estimate_url=estimation_call_back_url,
                              call_back_progress_url=progress_call_back_url,
                              log_extra=log_extra))
    webdav_client.mkdir(f'/{req.request_id}')

    save_request_metadata(req)
    webdav_client.upload_to(file.file, f'{req.request_id}/{req.original_document}')
    async_task = process_document.apply_async(
        (req.request_id, req.request_callback_info.to_dict(), remove_ocr_layer))

    webdav_client.mkdir(f'{req.request_id}/{task_ids}')
    register_task_id(webdav_client, req.request_id, async_task.id)

    return req.request_id


def load_request_metadata_or_raise(request_id: str) -> RequestMetadata:
    req = load_request_metadata(request_id)
    if not req:
        raise HTTPException(HTTP_404_NOT_FOUND, 'No such data extraction request.')
    return req


@app.delete('/api/v1/data_extraction_tasks/{request_id}/', response_model=TaskCancelResult,
            tags=["Asynchronous Data Extraction"])
async def purge_data_extraction_task(request_id: str):
    problems: dict = {}
    success: list = []
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


@app.get('/api/v1/data_extraction_tasks/{request_id}/status.json', response_model=RequestStatus,
         tags=["Asynchronous Data Extraction"])
async def get_request_status(request_id: str):
    return load_request_metadata_or_raise(request_id).to_request_status().to_dict()


@app.post('/api/v1/data_extraction_tasks/query_request_statuses',
          response_model=RequestStatuses,
          tags=["Asynchronous Data Extraction"])
async def query_multiple_request_statuses(request_ids: List[str]) -> RequestStatuses:
    if not request_ids:
        raise HTTPException(HTTP_400_BAD_REQUEST, 'Request ids must be specified.')
    statuses = []
    for request_id in request_ids:
        req = load_request_metadata(request_id)
        if req:
            statuses.append(req.to_request_status())
    return RequestStatuses(request_statuses=statuses).to_dict()


@app.post('/api/v1/data_extraction_tasks/query_request_summary',
          response_model=UserRequestsSummary,
          tags=["Asynchronous Data Extraction"])
async def query_user_requests(
        request: UserRequestsQuery) -> UserRequestsSummary:
    if not request.request_ids:
        raise HTTPException(HTTP_400_BAD_REQUEST, 'Request ids must be specified.')
    statuses = []
    for request_id, request_time in zip(request.request_ids, request.request_times):
        req = load_request_metadata(request_id)
        if req:
            req_status = req.to_request_status()
            setattr(req_status, 'started', request_time)
            statuses.append(req_status)

    # sort, trim and add summary
    sm = UserRequestsSummary(
        [], sum(1 for s in statuses if s.status == STATUS_PENDING))
    statuses.sort(key=lambda s: getattr(s, request.sort_column), reverse=request.sort_order == 'desc')
    end = request.records_on_page * request.page_index
    end = min(end, len(statuses))
    start = end - request.records_on_page
    start = max(start, 0)
    sm.request_statuses = statuses[start:end]
    return sm.to_dict()


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/packed_data.zip', tags=["Asynchronous Data Extraction"])
async def get_all_extracted_data_in_zip_archive(request_id: str):
    req: RequestMetadata = load_request_metadata_or_raise(request_id)
    mem_stream = pack_request_results(req)
    mem_stream.seek(0)
    response = StreamingResponse(mem_stream, media_type='application/x-zip-compressed')
    response.headers['Content-Disposition'] = 'attachment; filename=packed_data.zip'
    return response


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/extracted_tables.json',
         response_model=TableList, tags=["Asynchronous Data Extraction"])
async def get_extracted_tables_as_json(request_id: str):
    return _proxy_request(get_webdav_client(), request_id, load_request_metadata_or_raise(request_id).tables_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/extracted_tables.msgpack',
         responses={
             200: {
                 'description': 'TableList object in msgpack format.',
                 'content': {'application/octet-stream': {}},
             }
         }, tags=["Asynchronous Data Extraction"])
async def get_extracted_tables_as_msgpack(request_id: str):
    return _proxy_request(get_webdav_client(), request_id, load_request_metadata_or_raise(request_id).tables_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/extracted_tables.bin',
         responses={
             200: {
                 'description': 'TableList object in protobuf format.',
                 'content': {'application/octet-stream': {}},
             }
         }, tags=["Asynchronous Data Extraction"])
async def get_extracted_tables_as_protobuf(request_id: str):
    return _proxy_request(get_webdav_client(), request_id, load_request_metadata_or_raise(request_id).tables_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/extracted_plain_text.txt', response_model=AnyStr,
         tags=["Asynchronous Data Extraction"])
async def get_extracted_plain_text(request_id: str):
    return _proxy_request(get_webdav_client(),
                          request_id,
                          load_request_metadata_or_raise(request_id).plain_text_file,
                          headers={'Content-Type': 'text/plain; charset=utf-8'})


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/document_structure.json',
         response_model=PlainTextStructure, tags=["Asynchronous Data Extraction"])
async def get_extracted_text_structure_as_json(request_id: str):
    return _proxy_request(get_webdav_client(),
                          request_id,
                          load_request_metadata_or_raise(request_id).text_structure_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/document_structure.msgpack',
         responses={
             200: {
                 'description': 'PlainTextStructure object in msgpack format.',
                 'content': {'application/octet-stream': {}},
             }
         }, tags=["Asynchronous Data Extraction"])
async def get_extracted_text_structure_as_msgpack(request_id: str):
    return _proxy_request(get_webdav_client(),
                          request_id,
                          load_request_metadata_or_raise(request_id).text_structure_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/document_structure.bin',
         responses={
             200: {
                 'description': 'PlainTextStructure object in protobuf format.',
                 'content': {'application/octet-stream': {}},
             }
         }, tags=["Asynchronous Data Extraction"])
async def get_extracted_text_structure_as_protobuf(request_id: str):
    return _proxy_request(get_webdav_client(),
                          request_id,
                          load_request_metadata_or_raise(request_id).text_structure_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/pdf_coordinates.json',
         response_model=PDFCoordinates, tags=["Asynchronous Data Extraction"])
async def get_pdf_coordinates_of_each_character_in_extracted_plain_text_as_json(request_id: str):
    return _proxy_request(get_webdav_client(),
                          request_id,
                          load_request_metadata_or_raise(request_id).pdf_coordinates_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/pdf_coordinates.msgpack',
         responses={
             200: {
                 'description': 'PDFCoordinates object in msgpack format.',
                 'content': {'application/octet-stream': {}},
             }
         }, tags=["Asynchronous Data Extraction"])
async def get_pdf_coordinates_of_each_character_in_extracted_plain_text_as_msgpack(request_id: str):
    return _proxy_request(get_webdav_client(),
                          request_id,
                          load_request_metadata_or_raise(request_id).pdf_coordinates_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/pdf_coordinates.bin',
         responses={
             200: {
                 'description': 'PDFCoordinates object in protobuf format.',
                 'content': {'application/octet-stream': {}},
             }
         }, tags=["Asynchronous Data Extraction"])
async def get_pdf_coordinates_of_each_character_in_extracted_plain_text_as_protobuf(request_id: str):
    return _proxy_request(get_webdav_client(),
                          request_id,
                          load_request_metadata_or_raise(request_id).pdf_coordinates_file)


@app.get('/api/v1/data_extraction_tasks/{request_id}/results/searchable_pdf.pdf', tags=["Asynchronous Data Extraction"])
async def get_searchable_pdf(request_id: str):
    return _proxy_request(get_webdav_client(),
                          request_id,
                          load_request_metadata_or_raise(request_id).pdf_file)


@app.delete('/api/v1/data_extraction_tasks/{request_id}/results/', tags=["Asynchronous Data Extraction"])
async def delete_request_files(request_id: str):
    try:
        get_webdav_client().clean(f'{request_id}/')
    except RemoteResourceNotFound:
        raise HTTPException(HTTP_404_NOT_FOUND, 'No such data extraction request')


def pack_request_results(req: RequestMetadata) -> io.BytesIO:
    temp_dir = mkdtemp()
    try:
        files = [f'/{req.request_id}/{f}' for f in [req.plain_text_file, req.text_structure_file,
                                                    req.tables_file, req.pdf_coordinates_file,
                                                    req.pdf_file] if f]
        get_webdav_client().download_files(files, temp_dir)
        mem_stream = io.BytesIO()
        with zipfile.ZipFile(mem_stream, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for name_only in os.listdir(temp_dir):
                fn = os.path.join(temp_dir, name_only)
                if not os.path.isfile(fn):
                    continue
                zip_file.write(fn, arcname=name_only)
            zip_file.writestr(zinfo_or_arcname='status.json', data=req.to_request_status().to_json())
        return mem_stream
    finally:
        rmtree(temp_dir)


@app.post('/api/v1/extract/text_and_structure/', tags=["Synchronous Data Extraction"])
async def extract_all_data_from_document(
        file: UploadFile = File(...),
        doc_language: str = Form(default=''),
        convert_to_pdf_timeout_sec: int = Form(default=1800),
        pdf_to_images_timeout_sec: int = Form(default=1800),
        full_extract_timeout_sec: int = Form(default=3600),
        char_coords_debug_enable: bool = Form(default=False),
        output_format: OutputFormat = Form(default=OutputFormat.json),
        remove_ocr_layer: bool = Form(default=False),
):
    webdav_client = get_webdav_client()
    request_id = str(uuid4())
    _run_sync_pdf_processing(webdav_client, request_id, file, doc_language, convert_to_pdf_timeout_sec,
                             pdf_to_images_timeout_sec, char_coords_debug_enable, output_format, remove_ocr_layer)

    # Wait until celery finishes extracting else return TimeoutError
    if not _wait_for_pdf_extraction_finish(request_id, full_extract_timeout_sec):
        await purge_data_extraction_task(request_id)
        raise HTTPException(status_code=504, detail="Input file is too big")

    # Get all extracted data in .zip file and clean temp data
    req: RequestMetadata = load_request_metadata_or_raise(request_id)
    if req.status != dto.STATUS_DONE:
        raise HTTPException(status_code=500, detail=f'Request is not finished successfully.\n'
                                                    f'Status: {req.status}.\n'
                                                    f'Detail:\n{req.error_message}')
    mem_stream = pack_request_results(req)
    mem_stream.seek(0)
    response = StreamingResponse(mem_stream, media_type='application/x-zip-compressed')
    response.headers['Content-Disposition'] = 'attachment; filename=packed_data.zip'
    webdav_client.clean(f'{req.request_id}/')
    return response


@app.post('/api/v1/extract/plain_text/', tags=["Synchronous Data Extraction"])
async def extract_plain_text_from_document(
        file: UploadFile = File(...),
        doc_language: str = Form(default=''),
        convert_to_pdf_timeout_sec: int = Form(default=1800),
        pdf_to_images_timeout_sec: int = Form(default=1800),
        full_extract_timeout_sec: int = Form(default=3600),
        char_coords_debug_enable: bool = Form(default=False),
        output_format: OutputFormat = Form(default=OutputFormat.json),
        remove_ocr_layer: bool = Form(default=False),
):
    webdav_client = get_webdav_client()
    request_id = str(uuid4())
    _run_sync_pdf_processing(webdav_client, request_id, file, doc_language, convert_to_pdf_timeout_sec,
                             pdf_to_images_timeout_sec, char_coords_debug_enable, output_format, remove_ocr_layer)

    # Wait until celery finishes extracting else return TimeoutError
    if not _wait_for_pdf_extraction_finish(request_id, full_extract_timeout_sec):
        await purge_data_extraction_task(request_id)
        raise HTTPException(status_code=504, detail="Input file is too big")

    # Get extracted plain text and clean temp data
    plain_text = _proxy_request(webdav_client,
                                request_id,
                                load_request_metadata(request_id).plain_text_file,
                                headers={'Content-Type': 'text/plain; charset=utf-8'})
    webdav_client.clean(f'{request_id}/')
    return plain_text


@app.post('/api/v1/extract/searchable_pdf/', tags=["Synchronous Data Extraction"])
async def extract_text_from_document_and_generate_searchable_pdf(
        file: UploadFile = File(...),
        doc_language: str = Form(default=''),
        convert_to_pdf_timeout_sec: int = Form(default=1800),
        pdf_to_images_timeout_sec: int = Form(default=1800),
        full_extract_timeout_sec: int = Form(default=3600),
        char_coords_debug_enable: bool = Form(default=False),
        output_format: OutputFormat = Form(default=OutputFormat.json),
        remove_ocr_layer: bool = Form(default=False),
):
    webdav_client = get_webdav_client()
    request_id = str(uuid4())
    _run_sync_pdf_processing(webdav_client, request_id, file, doc_language, convert_to_pdf_timeout_sec,
                             pdf_to_images_timeout_sec, char_coords_debug_enable, output_format, remove_ocr_layer)

    # Wait until celery finishes extracting else return TimeoutError
    if not _wait_for_pdf_extraction_finish(request_id, full_extract_timeout_sec):
        await purge_data_extraction_task(request_id)
        raise HTTPException(status_code=504, detail="Input file is too big")

    # Get extracted text-based pdf file and clean temp data
    filename: str = load_request_metadata(request_id).pdf_file
    pdf_file: Response = _proxy_request(
        webdav_client=webdav_client,
        request_id=request_id,
        fn=filename,
        headers={
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename={filename}'
        }
    )
    webdav_client.clean(f'{request_id}/')
    return pdf_file


@app.get('/api/v1/system_info.json', response_model=SystemInfo, tags=["Others"])
async def get_system_info():
    return SystemInfo(version_number=version.VERSION_NUMBER,
                      git_branch=version.GIT_BRANCH,
                      git_commit=version.GIT_COMMIT,
                      lexnlp_git_branch=version.LEXNLP_GIT_BRANCH,
                      lexnlp_git_commit=version.LEXNLP_GIT_COMMIT,
                      build_date=version.BUILD_DATE,
                      python_version=sys.version,
                      pandas_version=pandas.__version__).to_dict()


@app.get('/api/v1/download_python_api_client', tags=["Others"])
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


def _proxy_request(webdav_client,
                   request_id: str,
                   fn: str,
                   headers: Dict[str, str] = None,
                   type_conversion: Optional[Callable[[Any], Any]] = None):
    try:
        resp: WebDavClient = webdav_client.execute_request('download', f'/{request_id}/{fn}')
        content = resp.content
        if content is not None and type_conversion:
            content = type_conversion(content)
        return Response(content=content, status_code=resp.status_code, headers=headers)
    except RemoteResourceNotFound:
        raise HTTPException(HTTP_404_NOT_FOUND, f'No such request or there is no filename `{fn}` in the request results')


def _wait_for_pdf_extraction_finish(request_id: str, timeout_sec: int) -> bool:
    """Wait until celery tasks finish
    """
    waiting_time_seconds = 0
    no_errors = True

    # Check finish_pdf_processing task status
    while load_request_metadata(request_id).status not in (STATUS_FAILURE, STATUS_DONE):
        # Get dynamic time_delay_sec and wait
        if waiting_time_seconds < 30:
            time_delay_sec = 3
        elif waiting_time_seconds < 5 * 60:
            time_delay_sec = 5
        elif waiting_time_seconds < 15 * 60:
            time_delay_sec = 10
        else:
            time_delay_sec = 15
        time.sleep(time_delay_sec)
        waiting_time_seconds += time_delay_sec
        # Check if processing takes too much time
        if waiting_time_seconds > timeout_sec:
            no_errors = False
            break
    return no_errors


def _run_sync_pdf_processing(webdav_client,
                             request_id: str,
                             file: UploadFile,
                             doc_language: str,
                             convert_to_pdf_timeout_sec: int,
                             pdf_to_images_timeout_sec: int,
                             char_coords_debug_enable: bool,
                             output_format: OutputFormat,
                             remove_ocr_layer: bool):
    """Run celery tasks to extract data from document
    """
    req = RequestMetadata(original_file_name=file.filename,
                          original_document=get_valid_fn(file.filename),
                          request_id=request_id,
                          request_date=datetime.now(),
                          doc_language=doc_language,
                          output_format=output_format,
                          convert_to_pdf_timeout_sec=convert_to_pdf_timeout_sec,
                          pdf_to_images_timeout_sec=pdf_to_images_timeout_sec,
                          char_coords_debug_enable=char_coords_debug_enable,
                          remove_ocr_layer=remove_ocr_layer,
                          request_callback_info=RequestCallbackInfo(
                              request_id=request_id,
                              original_file_name=file.filename))
    webdav_client.mkdir(f'/{req.request_id}')
    save_request_metadata(req)
    webdav_client.upload_to(file.file, f'{req.request_id}/{req.original_document}')
    async_task = process_document.apply_async(
        (req.request_id, req.request_callback_info.to_dict(), req.remove_ocr_layer)
    )
    webdav_client.mkdir(f'{req.request_id}/{task_ids}')
    register_task_id(webdav_client, req.request_id, async_task.id)

