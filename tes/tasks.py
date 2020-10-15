from uuid import uuid4

from celery import Celery

from .config import settings
from textract import process
from .file_storage import webdav_client

celery_app = Celery(
    'celery_app',
    backend=settings.celery_backend,
    broker=settings.celery_broker
)

celery_app.conf.update(task_track_started=True)


@celery_app.task(acks_late=True)
def process_document(request_id: str, file_name: str, call_back_url: str) -> bool:
    print(f'Starting text extraction for document {file_name}. Request uid: {request_id}')

    #webdav_client.download(f'/{request_id}/original_document')

    return True
