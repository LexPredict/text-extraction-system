import logging
import os
from tempfile import mkstemp
import pikepdf
import requests

from text_extraction_system.request_metadata import RequestMetadata
from .call_back_server import DocumentCallbackServer
from .testing_config import test_settings

log = logging.getLogger(__name__)


def test_basic_api_call_back():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'many_pages.odt')

    def assert_func(rfile, headers):
        log.info('Text extraction results are ready...')
        meta: RequestMetadata = RequestMetadata.from_json(rfile)
        assert meta.status == 'DONE'
        assert os.path.basename(fn) == meta.original_file_name
        assert meta.pdf_file == 'many_pages.converted.pdf'
        assert meta.tables_json_file is None
        assert meta.tika_xhtml_file == 'many_pages.tika.xhtml'
        assert meta.plain_text_file == 'many_pages.plain.txt'
        assert meta.call_back_additional_info == 'hello world'

        text = requests \
            .get(f'{test_settings.api_url}/api/v1/data_extraction_tasks/{meta.request_id}/{meta.plain_text_file}') \
            .text
        for i in range(1, 22):
            assert f'This is page {i}' in text

        tfd, tfn = mkstemp(suffix='.pdf')
        try:
            with requests \
                    .get(f'{test_settings.api_url}/api/v1/data_extraction_tasks/{meta.request_id}/{meta.pdf_file}') as r:
                r.raise_for_status()
                with open(tfn, 'wb') as tf:
                    for chunk in r.iter_content(chunk_size=8192):
                        tf.write(chunk)
            with pikepdf.open(tfn) as pdf:
                assert len(pdf.pages) == 22
        finally:
            os.remove(tfn)

        log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)
    resp = requests.post(test_settings.api_url + '/api/v1/data_extraction_tasks/',
                         files=dict(file=(os.path.basename(fn), open(fn, 'rb'))),
                         data=dict(call_back_url=f'http://{srv.bind_host}:{srv.bind_port}',
                                   call_back_additional_info='hello world'))
    if resp.status_code not in {200, 201}:
        resp.raise_for_status()
    srv.wait_for_test_results(60)


def test_basic_api_call_back2():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'tables.pdf')

    def assert_func(rfile, headers):
        log.info('Text extraction results are ready...')
        meta: RequestMetadata = RequestMetadata.from_json(rfile)
        assert meta.status == 'DONE'
        assert os.path.basename(fn) == meta.original_file_name
        assert meta.pdf_file == 'tables.ocred.pdf'
        assert meta.tables_json_file == 'tables.tables.json'
        assert meta.tika_xhtml_file == 'tables.tika.xhtml'
        assert meta.plain_text_file == 'tables.plain.txt'
        import json
        buf = requests \
            .get(f'{test_settings.api_url}/api/v1/data_extraction_tasks/{meta.request_id}/{meta.tables_json_file}') \
            .content
        tables = json.loads(buf)
        assert len(tables) == 6

        # Table on page 3 was originally an image. Testing tesseract with this.
        assert tables[-1]['page'] == 3

        log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)
    requests.post(test_settings.api_url + '/api/v1/data_extraction_tasks/',
                  files=dict(file=(os.path.basename(fn), open(fn, 'rb'))),
                  data=dict(call_back_url=f'http://{srv.bind_host}:{srv.bind_port}'))
    srv.wait_for_test_results(60)
