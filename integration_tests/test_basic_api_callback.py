import os
from typing import List, Dict
from zipfile import ZipFile

import requests

from text_extraction_system.request_metadata import metadata_fn, RequestMetadata
from .call_back_server import DocumentCallbackServer
from .testing_config import test_settings

import logging

log = logging.getLogger(__name__)


def test_basic_api_call_back():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'docx_simple.pdf')

    def assert_func(multipart_data: Dict[str, List]):
        log.info('Text extraction results received...')
        with ZipFile(multipart_data['file'][0].decode('ascii'), 'r') as z:
            file_names = {zi.filename for zi in z.filelist}
            log.info(f'Zip file contents: {file_names}')
            assert metadata_fn in file_names
            meta: RequestMetadata = RequestMetadata.from_json(z.read(metadata_fn))
            assert os.path.basename(fn) == meta.file_name

            assert meta.file_name_in_storage in file_names
            txt_fn = os.path.splitext(meta.file_name_in_storage)[0] + '.txt'
            assert txt_fn in file_names
            text: str = z.read(txt_fn).decode('utf-8')
            assert 'Heading' in text and 'Heading Lev 2' in text
            log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)
    requests.post(test_settings.api_url + '/api/v1/text_extraction_tasks/',
                  files=dict(file=(os.path.basename(fn), open(fn, 'rb'))),
                  data=dict(call_back_url=f'http://{srv.bind_host}:{srv.bind_port}'))
    srv.wait_for_test_results(5)
