import logging
import os
import shutil
import tempfile
from typing import List
from zipfile import ZipFile

import requests
from celery import Celery, chord
from textract import process

from text_extraction_system.config import get_settings
from text_extraction_system.constants import results_fn, page_blocks_for_ocr, page_blocks_ocred, metadata_fn
from text_extraction_system.convert_to_pdf import convert_to_pdf
from text_extraction_system.file_storage import get_webdav_client
from text_extraction_system.pdf_util import split_pdf_to_page_blocks, join_pdf_blocks
from text_extraction_system.request_metadata import RequestMetadata, save_request_metadata, load_request_metadata

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

    webdav_client = get_webdav_client()
    req: RequestMetadata = load_request_metadata(request_id)
    log.info(f'File name: {req.file_name}')
    with webdav_client.get_as_local_fn(f'{request_id}/{req.file_name_in_storage}') as (fn, _remote_path):
        if fn.lower().endswith('.pdf'):
            extract_text_and_finish(fn, req, webdav_client)
        else:
            with convert_to_pdf(fn) as pdf_fn:
                split_pdf_and_plan_processing(pdf_fn=pdf_fn, req=req)

    return True


def split_pdf_and_plan_processing(pdf_fn: str, req: RequestMetadata):
    page_block_size = settings.split_pdf_to_pages_block_size
    log.info(f'Splitting {pdf_fn} to blocks of {page_block_size} pages...')
    webdav_client = get_webdav_client()
    temp_dir = tempfile.mkdtemp()
    try:
        pdf_block_fns: List[str] = \
            split_pdf_to_page_blocks(src_pdf_fn=pdf_fn,
                                     dst_dir=temp_dir,
                                     pages_per_block=page_block_size,
                                     page_block_base_name=os.path.basename(req.file_name_in_storage)
                                     )
        webdav_client.mkdir(f'{req.request_id}/{page_blocks_for_ocr}')
        webdav_client.mkdir(f'{req.request_id}/{page_blocks_ocred}')
        for pdf_block_fn in pdf_block_fns:
            webdav_client.upload(f'{req.request_id}/{page_blocks_for_ocr}/{os.path.basename(pdf_block_fn)}',
                                 pdf_block_fn)
        req.page_block_file_names = [os.path.basename(fn) for fn in pdf_block_fns]
        save_request_metadata(req)

        log.info(f'Starting sub-tasks for OCR-ing pdf blocks:\n{", ".join(req.page_block_file_names)}')
        chord(ocr_pdf.s(req.request_id, fn)
              for fn in req.page_block_file_names)(join_pdfs_and_extract_text.s(req.request_id))

    finally:
        shutil.rmtree(temp_dir)


@celery_app.task(acks_late=True)
def ocr_pdf(request_id: str, pdf_fn: str):
    log.info(f'OCR-ing pdf block: {pdf_fn}...')
    webdav_client = get_webdav_client()

    with webdav_client.get_as_local_fn(f'{request_id}/{page_blocks_for_ocr}/{pdf_fn}') \
            as (local_pdf_fn, _remote_path):
        webdav_client.upload(f'{request_id}/{page_blocks_ocred}/{pdf_fn}', local_pdf_fn)
    return pdf_fn


@celery_app.task(acks_late=True)
def join_pdfs_and_extract_text(_processed_pdf_blocks: List[str], request_id: str):
    log.info(f'Re-combining OCR-ed pdf blocks and processing the text extraction for request {request_id}...')
    req: RequestMetadata = load_request_metadata(request_id)
    webdav_client = get_webdav_client()
    temp_dir = tempfile.mkdtemp()
    try:
        local_pdf_fns: List[str] = list()
        for pdf_fn in req.page_block_file_names:
            local_fn = os.path.join(temp_dir, pdf_fn)
            webdav_client.download(f'{request_id}/{page_blocks_ocred}/{pdf_fn}', local_fn)
            local_pdf_fns.append(local_fn)

        joined_pdf_fn = tempfile.mktemp(suffix='.pdf')
        try:
            join_pdf_blocks(local_pdf_fns, joined_pdf_fn)
            extract_text_and_finish(joined_pdf_fn, req, webdav_client)
        finally:
            os.remove(joined_pdf_fn)

    finally:
        shutil.rmtree(temp_dir)


def extract_text_and_finish(pdf_fn: str, req: RequestMetadata, webdav_client):
    text: bytes = process(pdf_fn)
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
