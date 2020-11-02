import logging
import os
from typing import List, Dict
from zipfile import ZipFile
from io import BytesIO
import pikepdf
import requests

from text_extraction_system.request_metadata import metadata_fn, RequestMetadata
from .call_back_server import DocumentCallbackServer
from .testing_config import test_settings

log = logging.getLogger(__name__)


def test_basic_api_call_back():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'many_pages.odt')

    def assert_func(multipart_data: Dict[str, List]):
        log.info('Text extraction results received...')
        with ZipFile(multipart_data['file'][0].decode('ascii'), 'r') as z:
            file_names = {zi.filename for zi in z.filelist}
            log.info(f'Zip file contents: {file_names}')
            assert metadata_fn in file_names
            meta: RequestMetadata = RequestMetadata.from_json(z.read(metadata_fn))
            assert os.path.basename(fn) == meta.file_name

            assert os.path.splitext(meta.file_name_in_storage)[0] + '.pdf' in file_names
            txt_fn = os.path.splitext(meta.file_name_in_storage)[0] + '.txt'
            assert txt_fn in file_names
            pdf_fn = os.path.splitext(meta.file_name_in_storage)[0] + '.pdf'
            assert pdf_fn in file_names

            text: str = z.read(txt_fn).decode('utf-8')
            for i in range(1, 22):
                assert f'This is page {i}' in text

            buf = BytesIO()
            buf.write(z.read(os.path.splitext(meta.file_name_in_storage)[0] + '.pdf'))
            with pikepdf.open(buf) as pdf:
                assert len(pdf.pages) == 22

            log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)
    requests.post(test_settings.api_url + '/api/v1/text_extraction_tasks/',
                  files=dict(file=(os.path.basename(fn), open(fn, 'rb'))),
                  data=dict(call_back_url=f'http://{srv.bind_host}:{srv.bind_port}'))
    srv.wait_for_test_results(5)
