import logging
import os
import shutil
import tempfile
from typing import List, Dict
from zipfile import ZipFile

import requests
from celery import Celery, chord

from text_extraction_system.config import get_settings
from text_extraction_system.constants import results_fn, pages_for_ocr, pages_ocred, metadata_fn
from text_extraction_system.pdf.convert_to_pdf import convert_to_pdf
from text_extraction_system.file_storage import get_webdav_client, WebDavClient
from text_extraction_system.pdf.pdf import find_pages_requiring_ocr, \
    extract_page_images, ocr_page_to_pdf, merge_pfd_pages
from text_extraction_system.request_metadata import RequestMetadata, save_request_metadata, load_request_metadata
from text_extraction_system.data_extract.tika import tika_extract_xhtml

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
    log.info(f'File name: {req.file_name}')
    with webdav_client.get_as_local_fn(f'{request_id}/{req.file_name_in_storage}') as (fn, _remote_path):
        ext = os.path.splitext(fn)[1]
        if ext and ext.lower() == '.pdf':
            req.pdf_name_in_storage = req.file_name_in_storage
            save_request_metadata(req)
            process_pdf(pdf_fn=fn, req=req, webdav_client=webdav_client)
        else:
            with convert_to_pdf(fn) as local_converted_pdf_fn:
                req.pdf_name_in_storage = os.path.splitext(req.file_name_in_storage)[0] + '.pdf'
                webdav_client.upload(f'{request_id}/{req.pdf_name_in_storage}', local_converted_pdf_fn)
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
    log.info(f'Re-combining OCR-ed pdf blocks and processing the text extraction for request {request_id}...')
    req: RequestMetadata = load_request_metadata(request_id)
    webdav_client = get_webdav_client()
    temp_dir = tempfile.mkdtemp()
    try:
        pages_dir = os.path.join(temp_dir, 'pages')
        os.mkdir(pages_dir)
        repl_page_num_to_fn: Dict[int, str] = dict()
        for page_num, image_fn in req.pages_for_ocr.values():
            basename = os.path.splitext(image_fn)[0] + '.pdf'
            remote_page_pdf_fn = f'{req.request_id}/{pages_ocred}/{basename}'
            local_page_pdf_fn = os.path.join(pages_dir, basename)
            webdav_client.download(remote_page_pdf_fn, local_page_pdf_fn)
            repl_page_num_to_fn[page_num] = local_page_pdf_fn

        local_orig_pdf_fn = os.path.join(temp_dir, req.pdf_name_in_storage)
        req.ocred_pdf_name_in_storage = os.path.splitext(req.pdf_name_in_storage)[0] + '.ocr.pdf'

        webdav_client.download(f'{req.request_id}/{req.pdf_name_in_storage}', local_orig_pdf_fn)
        with merge_pfd_pages(local_orig_pdf_fn, repl_page_num_to_fn) as local_merged_pdf_fn:
            webdav_client.upload(f'{req.request_id}/{req.ocred_pdf_name_in_storage}', local_merged_pdf_fn)
            save_request_metadata(req)
            extract_text_from_ocred_pdf_and_finish(local_merged_pdf_fn, req, webdav_client)

    finally:
        shutil.rmtree(temp_dir)


def extract_text_from_ocred_pdf_and_finish(pdf_fn: str, req: RequestMetadata, webdav_client):
    text: str = tika_extract_xhtml(pdf_fn)
    req.tika_xhtml_name_in_storage
    print(f'Text: {text[:200]}')
    zip_fn = tempfile.mktemp(suffix='.zip')
    try:
        with ZipFile(zip_fn, 'w') as zip_archive:
            zip_archive.writestr(metadata_fn, req.to_json(indent=2))
            text_fn = os.path.splitext(req.file_name_in_storage)[0] + '.txt'
            zip_archive.writestr(text_fn, text)
            zip_archive.write(pdf_fn, os.path.splitext(req.file_name_in_storage)[0] + '.pdf')

        webdav_client.upload(f'{req.request_id}/{results_fn}', zip_fn)
        if req.call_back_url:
            log.info(f'POSTing the extraction results of {req.file_name} to {req.call_back_url}...')
            requests.post(req.call_back_url, files=dict(file=zip_fn))
        log.info(f'Finished processing request {req.request_id} ({req.file_name}).')
    finally:
        os.remove(pdf_fn)
