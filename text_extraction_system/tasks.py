import os
import tempfile
from io import BytesIO
from zipfile import ZipFile

import requests
from celery import Celery
from textract import process

from .config import settings
from .file_storage import webdav_client, get_as_local_fn
from .request_metadata import RequestMetadata, metadata_fn, results_fn

celery_app = Celery(
    'celery_app',
    backend=settings.celery_backend,
    broker=settings.celery_broker
)

celery_app.conf.update(task_track_started=True)


@celery_app.task(acks_late=True)
def process_document(request_id: str) -> bool:
    print(f'Starting text extraction for request uid: {request_id}')

    buf = BytesIO()
    webdav_client.download_from(buf, f'{request_id}/{metadata_fn}')
    meta: RequestMetadata = RequestMetadata.from_json(buf.getvalue())
    print(f'File name: {meta.file_name}')
    with get_as_local_fn(f'{request_id}/{meta.file_name_in_storage}') as (fn, _remote_path):
        text: bytes = process(fn)
        print(f'Text: {text[:200]}')

        _fd, fn = tempfile.mkstemp(suffix='.zip')
        try:
            with ZipFile(fn, 'w') as zip_archive:
                zip_archive.writestr(metadata_fn, meta.to_json(indent=2))
                text_fn = os.path.splitext(meta.file_name_in_storage)[0] + '.txt'
                zip_archive.writestr(text_fn, text)
                zip_archive.write(fn, meta.file_name_in_storage)

            webdav_client.upload(f'{request_id}/{results_fn}', fn)
            if meta.call_back_url:
                requests.post(meta.call_back_url, files=dict(file=fn))
        finally:
            os.remove(fn)

    return True
