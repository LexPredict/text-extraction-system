import os
import tempfile
from io import BytesIO
from zipfile import ZipFile

import requests
from celery import Celery
from textract import process

from text_extraction_system.config import get_settings
from text_extraction_system.convert_to_pdf import convert_to_pdf
from text_extraction_system.file_storage import get_webdav_client
from text_extraction_system.request_metadata import RequestMetadata, metadata_fn, results_fn

settings = get_settings()

celery_app = Celery(
    'celery_app',
    backend=settings.celery_backend,
    broker=settings.celery_broker
)

celery_app.conf.update(task_track_started=True)


@celery_app.task(acks_late=True)
def process_document(request_id: str) -> bool:
    print(f'Starting text extraction for request uid: {request_id}')

    webdav_client = get_webdav_client()
    buf = BytesIO()
    webdav_client.download_from(buf, f'{request_id}/{metadata_fn}')
    meta: RequestMetadata = RequestMetadata.from_json(buf.getvalue())
    print(f'File name: {meta.file_name}')
    with webdav_client.get_as_local_fn(f'{request_id}/{meta.file_name_in_storage}') as (fn, _remote_path):
        if fn.lower().endswith('.pdf'):
            process_local_file(fn, meta, webdav_client)
        else:
            with convert_to_pdf(fn) as pdf_fn:
                process_local_file(pdf_fn, meta, webdav_client)

    return True


def process_local_file(pdf_fn, meta, webdav_client):
    text: bytes = process(pdf_fn)
    print(f'Text: {text[:200]}')
    _fd, pdf_fn = tempfile.mkstemp(suffix='.zip')
    try:
        with ZipFile(pdf_fn, 'w') as zip_archive:
            zip_archive.writestr(metadata_fn, meta.to_json(indent=2))
            text_fn = os.path.splitext(meta.file_name_in_storage)[0] + '.txt'
            zip_archive.writestr(text_fn, text)
            zip_archive.write(pdf_fn, os.path.splitext(meta.file_name_in_storage)[0] + '.pdf')

        webdav_client.upload(f'{meta.request_id}/{results_fn}', pdf_fn)
        if meta.call_back_url:
            requests.post(meta.call_back_url, files=dict(file=pdf_fn))
    finally:
        os.remove(pdf_fn)
