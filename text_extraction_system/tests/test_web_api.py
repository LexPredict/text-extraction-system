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
    file_storage._webdav_client = MockWebDavClient()
    with patch.object(file_storage._webdav_client, 'upload_to') as upload_to_method:
        with patch.object(file_storage._webdav_client, 'mkdir') as mkdir_method:
            with patch.object(file_storage._webdav_client, 'download_from') as download_method:
                download_method.side_effect = StopHereException()
                from text_extraction_system.web_api import post_text_extraction_task
                from fastapi import UploadFile

                with pytest.raises(StopHereException):
                    await post_text_extraction_task(UploadFile(filename='test.pdf'), 'return_url')

                mkdir_method.assert_called_once()
                upload_to_method.assert_called()
