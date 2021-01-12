from unittest.mock import patch

import pytest

from text_extraction_system import config
from text_extraction_system import file_storage


@pytest.fixture()
def setup():
    config._settings = config.Settings.construct(webdav_url='', webdav_username='', webdav_password='',
                                                 celery_broker='', celery_backend='')
    from text_extraction_system import tasks
    tasks.celery_app.conf.update(task_always_eager=True)
    yield True


class StopHereException(Exception):
    pass


@pytest.mark.asyncio
async def test_webapi_calls_process_document(setup):
    from text_extraction_system.commons.tests.commons import MockWebDavClient
    from text_extraction_system.tasks import process_document
    file_storage._webdav_client = MockWebDavClient()
    with patch.object(file_storage._webdav_client, 'upload_to') as upload_to_method:
        with patch.object(file_storage._webdav_client, 'mkdir') as mkdir_method:
            with patch.object(process_document, 'apply_async') as apply_async_method:
                from text_extraction_system.web_api import post_text_extraction_task
                from fastapi import UploadFile

                await post_text_extraction_task(UploadFile(filename='test.pdf'),
                                                call_back_celery_version=None,
                                                call_back_additional_info=None,
                                                call_back_url='return_url',
                                                call_back_celery_broker=None,
                                                call_back_celery_parent_task_id=None,
                                                call_back_celery_queue=None,
                                                call_back_celery_root_task_id=None,
                                                call_back_celery_task_id=None,
                                                call_back_celery_task_name=None,
                                                doc_language=None,
                                                ocr_enable=True,
                                                log_extra_json_key_value='null'
                                                )
                mkdir_method.assert_called()
                upload_to_method.assert_called()
                apply_async_method.assert_called_once()
