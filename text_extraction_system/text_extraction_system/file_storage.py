import os
import pickle
import tempfile
from contextlib import contextmanager
from io import BytesIO
from typing import Optional, Any

from webdav3.client import Client

from text_extraction_system.config import get_settings


class WebDavClient(Client):

    def __init__(self):
        settings = get_settings()

        super().__init__({
            'webdav_hostname': settings.webdav_url,
            'webdav_login': settings.webdav_username,
            'webdav_password': settings.webdav_password,
        })

    def unpickle(self, remote_path: str) -> Any:
        bytes_io = BytesIO()
        self.download_from(bytes_io, remote_path)
        return pickle.loads(bytes_io.getvalue())

    def pickle(self, obj: Any, remote_path: str) -> Any:
        self.upload_to(pickle.dumps(obj), remote_path)

    @contextmanager
    def get_as_local_fn(self, remote_path: str):
        _, ext = os.path.splitext(remote_path)
        _fd, fn = tempfile.mkstemp(suffix=ext)
        try:
            self.download(remote_path=remote_path, local_path=fn)
            yield fn, remote_path
        finally:
            os.remove(fn)


_webdav_client: Optional[WebDavClient] = None


def get_webdav_client():
    global _webdav_client
    if not _webdav_client:
        _webdav_client = WebDavClient()
    return _webdav_client
