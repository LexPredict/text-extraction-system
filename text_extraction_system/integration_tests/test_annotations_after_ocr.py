import logging
import os

import pikepdf
from text_extraction_system_api.client import TextExtractionSystemWebClient
from text_extraction_system_api.dto import RequestStatus, PlainTextStructure, OutputFormat

from integration_tests.call_back_server import DocumentCallbackServer
from integration_tests.testing_config import test_settings

log = logging.getLogger(__name__)


def test_annotations_after_pdf_ocr():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'with_annotations.pdf')
    client = TextExtractionSystemWebClient(test_settings.api_url)

    def assert_func(rfile, headers):
        log.info('Text extraction results are ready...')
        rs: RequestStatus = RequestStatus.from_json(rfile)
        assert rs.status == 'DONE'
        assert os.path.basename(fn) == rs.original_file_name
        assert rs.converted_cleaned_pdf is False
        assert rs.tables_extracted is False
        assert rs.plain_text_extracted
        assert rs.text_structure_extracted

        with client.get_pdf_as_local_file(rs.request_id) as tfn:
            fn_pdf = pikepdf.open(fn)
            with pikepdf.open(tfn), pikepdf.open(fn) as tfn_pdf, fn_pdf:
                assert len(tfn_pdf.pages) == len(fn_pdf.pages)
                assert len(tfn_pdf.pages) == 3
                assert tfn_pdf.pages[0]['/Annots']
                assert tfn_pdf.pages[0]['/Annots'] == fn_pdf.pages[0]['/Annots']

        text_struct: PlainTextStructure = client.get_extracted_text_structure_as_msgpack(rs.request_id)
        assert len(text_struct.pages) == 3
        assert len(text_struct.paragraphs) == 9

        log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)

    request_id = client.schedule_data_extraction_task(fn,
                                                      call_back_url=f'http://{srv.bind_host}:{srv.bind_port}',
                                                      call_back_additional_info='hello world',
                                                      doc_language='en',
                                                      log_extra={'hello': 'world', 'test': True},
                                                      output_format=OutputFormat.msgpack)
    srv.wait_for_test_results(120)

    # the following additionally tests if we are able to delete directories
    client.delete_data_extraction_task_files(request_id)
