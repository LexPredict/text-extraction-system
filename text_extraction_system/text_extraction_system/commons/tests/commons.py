from contextlib import contextmanager
from typing import Generator

from text_extraction_system import config


class MockWebDavClient():
    def upload_to(self, *args, **kwargs):
        print('upload_to called')

    def mkdir(self, *args, **kwargs):
        print('mkdir called')

    def download_from(self, *args, **kwargs):
        print('download_from called')


@contextmanager
def default_settings() -> Generator[config.Settings, None, None]:
    config._settings = config.Settings.construct(webdav_url='',
                                                 webdav_username='',
                                                 webdav_password='',
                                                 celery_broker='',
                                                 celery_backend='')
    yield config._settings


def with_default_settings(func):
    def wrapper(*args, **kwargs):
        with default_settings():
            func(*args, **kwargs)

    return wrapper
