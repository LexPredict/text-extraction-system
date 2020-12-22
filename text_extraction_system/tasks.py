import json
import logging
import os
import shutil
import tempfile
from typing import List, Dict

import requests
from celery import Celery, chord

from text_extraction_system.config import get_settings
from text_extraction_system.constants import pages_for_ocr, pages_ocred
from text_extraction_system.data_extract.data_extract import tika_extract_xhtml, extract_text_pdfminer, \
    get_tables_from_pdf_camelot
from text_extraction_system.file_storage import get_webdav_client, WebDavClient
from text_extraction_system.ocr.ocr import ocr_page_to_pdf
from text_extraction_system.pdf.convert_to_pdf import convert_to_pdf
from text_extraction_system.pdf.pdf import find_pages_requiring_ocr, \
    extract_page_images, merge_pfd_pages
from text_extraction_system.request_metadata import RequestMetadata, STATUS_DONE, save_request_metadata, \
    load_request_metadata
from text_extraction_system.result_delivery.celery_client import send_task

settings = get_settings()

celery_app = Celery(
    'celery_app',
    backend=settings.celery_backend,
    broker=settings.celery_broker
)

celery_app.conf.update(task_track_started=True)

log = logging.getLogger(__name__)


@celery_app.task(acks_late=True)
def process_document(request_id: str) -> bool:
    log.info(f'Starting text extraction for request uid: {request_id}')

    webdav_client: WebDavClient = get_webdav_client()
    req: RequestMetadata = load_request_metadata(request_id)
    log.info(f'File name: {req.original_file_name}')
    with webdav_client.get_as_local_fn(f'{request_id}/{req.original_document}') as (fn, _remote_path):
        ext = os.path.splitext(fn)[1]
        if ext and ext.lower() == '.pdf':
            process_pdf(pdf_fn=fn, req=req, webdav_client=webdav_client)
        else:
            with convert_to_pdf(fn) as local_converted_pdf_fn:
                req.converted_to_pdf = os.path.splitext(req.original_document)[0] + '.converted.pdf'
                webdav_client.upload(f'{request_id}/{req.converted_to_pdf}', local_converted_pdf_fn)
                save_request_metadata(req)
                process_pdf(local_converted_pdf_fn, req, webdav_client)

    return True


def process_pdf(pdf_fn: str, req: RequestMetadata, webdav_client: WebDavClient):
    pages_to_ocr = find_pages_requiring_ocr(pdf_fn)
    if pages_to_ocr:
        split_pdf_and_schedule_ocr(pdf_fn=pdf_fn, req=req, pages_to_ocr=pages_to_ocr)
    else:
        extract_text_from_ocred_pdf_and_finish(pdf_fn, req, webdav_client)


def split_pdf_and_schedule_ocr(pdf_fn: str, req: RequestMetadata, pages_to_ocr: List[int]):
    log.info(f'Extracting pages requiring OCR from {pdf_fn}:\n{pages_to_ocr}')
    webdav_client = get_webdav_client()
    webdav_client.mkdir(f'{req.request_id}/{pages_for_ocr}')
    webdav_client.mkdir(f'{req.request_id}/{pages_ocred}')
    ocr_language = req.doc_language or 'eng'
    req.pages_for_ocr = dict()
    task_signatures = list()
    for page_num, image_fn in extract_page_images(pdf_fn, pages_to_ocr):
        basename = os.path.basename(image_fn)
        webdav_client.upload(f'{req.request_id}/{pages_for_ocr}/{basename}',
                             image_fn)
        req.pages_for_ocr[page_num] = basename
        dst_basename = os.path.splitext(basename)[0] + '.pdf'
        task_signatures.append(ocr_image.s(f'{req.request_id}/{pages_for_ocr}/{basename}',
                                           f'{req.request_id}/{pages_ocred}/{dst_basename}',
                                           ocr_language))

    save_request_metadata(req)
    log.info(f'Starting sub-tasks for OCR-ing pdf pages:\n{req.pages_for_ocr}')
    chord(task_signatures)(merge_ocred_pages_and_extract_text.s(req.request_id))


@celery_app.task(acks_late=True)
def ocr_image(page_image_webdav_path: str, page_pdf_dst_webdav_path: str, ocr_language: str = 'eng'):
    log.info(f'OCR-ing image: {page_image_webdav_path}...')
    webdav_client = get_webdav_client()

    with webdav_client.get_as_local_fn(page_image_webdav_path) \
            as (local_image_src, _remote_path):
        with ocr_page_to_pdf(local_image_src, language=ocr_language) as local_pdf_fn:
            webdav_client.upload(page_pdf_dst_webdav_path, local_pdf_fn)
    return page_pdf_dst_webdav_path


@celery_app.task(acks_late=True)
def merge_ocred_pages_and_extract_text(_ocred_page_paths: List[str], request_id: str):
    req: RequestMetadata = load_request_metadata(request_id)
    log.info(f'Re-combining OCR-ed pdf blocks and processing the text extraction for request {request_id}: '
             f'{req.original_file_name}')
    webdav_client = get_webdav_client()
    temp_dir = tempfile.mkdtemp()
    try:
        pages_dir = os.path.join(temp_dir, 'pages')
        os.mkdir(pages_dir)
        repl_page_num_to_fn: Dict[int, str] = dict()
        for page_num, image_fn in req.pages_for_ocr.items():
            basename = os.path.splitext(image_fn)[0] + '.pdf'
            remote_page_pdf_fn = f'{req.request_id}/{pages_ocred}/{basename}'
            local_page_pdf_fn = os.path.join(pages_dir, basename)
            webdav_client.download(remote_page_pdf_fn, local_page_pdf_fn)
            repl_page_num_to_fn[page_num] = local_page_pdf_fn

        original_pdf_in_storage = req.converted_to_pdf or req.original_document
        local_orig_pdf_fn = os.path.join(temp_dir, original_pdf_in_storage)
        req.ocred_pdf = os.path.splitext(original_pdf_in_storage)[0] + '.ocred.pdf'

        webdav_client.download(f'{req.request_id}/{original_pdf_in_storage}', local_orig_pdf_fn)
        with merge_pfd_pages(local_orig_pdf_fn, repl_page_num_to_fn) as local_merged_pdf_fn:
            webdav_client.upload(f'{req.request_id}/{req.ocred_pdf}', local_merged_pdf_fn)
            save_request_metadata(req)
            extract_text_from_ocred_pdf_and_finish(local_merged_pdf_fn, req, webdav_client)

    finally:
        shutil.rmtree(temp_dir)


def extract_text_from_ocred_pdf_and_finish(pdf_fn: str, req: RequestMetadata, webdav_client: WebDavClient):
    req.pdf = req.ocred_pdf or req.converted_to_pdf or req.original_document
    pdf_fn_in_storage_base = os.path.splitext(req.original_document)[0]

    tika_xhtml: str = tika_extract_xhtml(pdf_fn)
    req.tika_xhtml = pdf_fn_in_storage_base + '.tika.xhtml'
    webdav_client.upload_to(tika_xhtml, f'{req.request_id}/{req.tika_xhtml}')

    text: str = extract_text_pdfminer(pdf_fn)
    req.plain_text = pdf_fn_in_storage_base + '.plain.txt'
    webdav_client.upload_to(text, f'{req.request_id}/{req.plain_text}')

    tables = get_tables_from_pdf_camelot(pdf_fn)
    if tables:
        tables = json.dumps([t.to_dict() for t in get_tables_from_pdf_camelot(pdf_fn)], indent=2)
        req.tables = pdf_fn_in_storage_base + '.tables.json'
        webdav_client.upload_to(tables, f'{req.request_id}/{req.tables}')

    if settings.delete_temp_files_on_request_finish:
        if req.converted_to_pdf and req.converted_to_pdf != req.pdf:
            webdav_client.clean(f'{req.request_id}/{req.converted_to_pdf}')
        if req.ocred_pdf and req.ocred_pdf != req.pdf:
            webdav_client.clean(f'{req.request_id}/{req.ocred_pdf}')
        if req.pages_for_ocr:
            webdav_client.clean(f'{req.request_id}/{pages_for_ocr}')
            webdav_client.clean(f'{req.request_id}/{pages_ocred}')

    req.converted_to_pdf = None
    req.ocred_pdf = None
    req.status = STATUS_DONE

    save_request_metadata(req)

    response_meta = {k: v for k, v in req.to_dict().items() if v is not None}

    if req.call_back_url:
        log.info(f'POSTing the extraction results of {req.original_file_name} to {req.call_back_url}...')
        requests.post(req.call_back_url, json=response_meta)

    if req.call_back_celery_broker:
        log.info(f'Sending a celery task\n'
                 f'broker: {req.call_back_celery_broker}\n'
                 f'queue: {req.call_back_celery_queue}\n'
                 f'task_name: {req.call_back_celery_task_name}\n')
        send_task(broker_url=req.call_back_celery_broker,
                  queue=req.call_back_celery_queue,
                  task_name=req.call_back_celery_task_name,
                  task_kwargs=response_meta,
                  task_id=req.call_back_celery_task_id,
                  parent_task_id=req.call_back_celery_parent_task_id,
                  root_task_id=req.call_back_celery_root_task_id,
                  celery_version=req.call_back_celery_version)

    log.info(f'Finished processing request {req.request_id} ({req.original_file_name}).')
