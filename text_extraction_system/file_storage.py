import os
import re
import tempfile
from contextlib import contextmanager

from webdav3.client import Client

from .config import settings

options = {
    'webdav_hostname': settings.webdav_url,
    'webdav_login': settings.webdav_username,
    'webdav_password': settings.webdav_password
}

webdav_client = Client(options)


def get_valid_fn(s: str) -> str:
    """
    Return valid escaped filename from a string.
    Removes path separators and "..". Shortens to max 64 characters.
    Tries to keep the original extension.

    Based on the function with the same name from Django Framework.
    """
    fn, ext = os.path.splitext(str(s))
    fn, ext = [re.sub(r'(?u)[^-_\w]', '_', str(ss).strip().replace(' ', '_'))
               for ss in [fn, ext.strip('.')]]
    return fn + '.' + ext if ext else fn


@contextmanager
def get_as_local_fn(remote_path: str):
    _, ext = os.path.splitext(remote_path)
    _fd, fn = tempfile.mkstemp(suffix=ext)
    try:
        webdav_client.download(remote_path=remote_path, local_path=fn)
        yield fn, remote_path
    finally:
        os.remove(fn)
