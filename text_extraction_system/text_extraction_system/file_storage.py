import io
import os
import pickle
import tempfile
import zipfile
from contextlib import contextmanager
from io import BytesIO
from shutil import rmtree
from typing import Optional, Any, List

from webdav3.client import Client, wrap_connection_error, Urn, MethodNotSupported, WebDavXmlUtils, \
    LocalResourceNotFound, OptionNotValid

from text_extraction_system.config import get_settings


class WebDavClient(Client):

    def __init__(self):
        settings = get_settings()

        super().__init__({
            'webdav_hostname': settings.webdav_url,
            'webdav_login': settings.webdav_username,
            'webdav_password': settings.webdav_password,
            'disable_check': True
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
            self.download_file(remote_path=remote_path, local_path=fn)
            yield fn, remote_path
        finally:
            os.remove(fn)

    @wrap_connection_error
    def mkdir(self, remote_path):
        # copy-pasted from the webdav lib with the non-needed additional http queries returned
        directory_urn = Urn(remote_path, directory=True)
        try:
            response = self.execute_request(action='mkdir', path=directory_urn.quote())
        except MethodNotSupported:
            # Yandex WebDAV returns 405 status code when directory already exists
            return True
        return response.status_code in (200, 201)

    @wrap_connection_error
    def list(self, remote_path=Client.root, get_info=False):
        # copy-pasted from the webdav lib with the non-needed additional http queries returned

        directory_urn = Urn(remote_path, directory=True)

        path = Urn.normalize_path(self.get_full_path(directory_urn))
        response = self.execute_request(action='list', path=directory_urn.quote())
        if get_info:
            subfiles = WebDavXmlUtils.parse_get_list_info_response(response.content)
            return [subfile for subfile in subfiles if Urn.compare_path(path, subfile.get('path')) is False]

        urns = WebDavXmlUtils.parse_get_list_response(response.content)

        return [urn.filename() for urn in urns if Urn.compare_path(path, urn.path()) is False]

    @wrap_connection_error
    def download_file(self, remote_path, local_path, progress=None):
        # copy-pasted from the webdav lib with the non-needed additional http queries returned

        urn = Urn(remote_path)
        with open(local_path, 'wb') as local_file:
            response = self.execute_request('download', urn.quote())
            for block in response.iter_content(1024):
                local_file.write(block)

    @wrap_connection_error
    def download_packed_files(self, remote_paths: List[str]) -> io.BytesIO:
        # copy-pasted from the webdav lib with the non-needed additional http queries returned
        temp_dir = tempfile.mkdtemp()
        try:
            for remote_path in remote_paths:
                urn = Urn(remote_path)
                file_name = os.path.join(temp_dir, os.path.basename(remote_path))
                with open(file_name, 'wb') as local_file:
                    response = self.execute_request('download', urn.quote())
                    for block in response.iter_content(1024):
                        local_file.write(block)

            mem_stream = io.BytesIO()
            with zipfile.ZipFile(mem_stream, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for name_only in os.listdir(temp_dir):
                    fn = os.path.join(temp_dir, name_only)
                    if not os.path.isfile(fn):
                        continue
                    zip_file.write(fn, arcname=name_only)
            return mem_stream
        finally:
            rmtree(temp_dir)

    @wrap_connection_error
    def upload_file(self, remote_path, local_path, progress=None):
        # copy-pasted from the webdav lib with the non-needed additional http queries returned

        if not os.path.exists(local_path):
            raise LocalResourceNotFound(local_path)

        urn = Urn(remote_path)
        if urn.is_dir():
            raise OptionNotValid(name="remote_path", value=remote_path)

        if os.path.isdir(local_path):
            raise OptionNotValid(name="local_path", value=local_path)

        with open(local_path, "rb") as local_file:
            self.execute_request(action='upload', path=urn.quote(), data=local_file)

    @wrap_connection_error
    def upload_to(self, buff, remote_path):
        # copy-pasted from the webdav lib with the non-needed additional http queries returned

        urn = Urn(remote_path)
        if urn.is_dir():
            raise OptionNotValid(name="remote_path", value=remote_path)

        self.execute_request(action='upload', path=urn.quote(), data=buff)

    @wrap_connection_error
    def download_from(self, buff, remote_path):
        # copy-pasted from the webdav lib with the non-needed additional http queries returned

        urn = Urn(remote_path)
        response = self.execute_request(action='download', path=urn.quote())
        for chunk in response.iter_content(chunk_size=128):
            buff.write(chunk)


_webdav_client: Optional[WebDavClient] = None


def get_webdav_client():
    global _webdav_client
    if not _webdav_client:
        _webdav_client = WebDavClient()
    return _webdav_client
