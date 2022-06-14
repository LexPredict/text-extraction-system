import logging
import os
import unittest

import pikepdf
from text_extraction_system_api.client import TextExtractionSystemWebClient
from text_extraction_system_api.dto import RequestStatus, PlainTextStructure, OutputFormat

from integration_tests.call_back_server import DocumentCallbackServer
from integration_tests.testing_config import test_settings

log = logging.getLogger(__name__)


class TestAnnotationsAfterOCR(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TextExtractionSystemWebClient(test_settings.api_url)
        self.srv = DocumentCallbackServer()
        self.call_back_url = f'http://{self.srv.bind_host}:{self.srv.bind_port}'

    def test_annotations_after_pdf_ocr(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'with_annotations.pdf')

        def assert_func(rs_id: str):
            rs: RequestStatus = self.client.get_data_extraction_task_status(rs_id)
            assert rs.status == 'DONE'
            assert os.path.basename(fn) == rs.original_file_name
            assert rs.converted_cleaned_pdf is False
            assert rs.tables_extracted is False
            assert rs.plain_text_extracted
            assert rs.text_structure_extracted

            with self.client.get_pdf_as_local_file(rs.request_id) as tfn:
                fn_pdf = pikepdf.open(fn)
                with pikepdf.open(tfn), pikepdf.open(fn) as tfn_pdf, fn_pdf:
                    assert len(tfn_pdf.pages) == len(fn_pdf.pages)
                    assert len(tfn_pdf.pages) == 3
                    assert tfn_pdf.pages[0]['/Annots']
                    assert tfn_pdf.pages[0]['/Annots'] == fn_pdf.pages[0]['/Annots']

            text_struct: PlainTextStructure = self.client.get_extracted_text_structure_as_msgpack(
                rs.request_id)
            assert len(text_struct.pages) == 3
            assert len(text_struct.paragraphs) == 9

            log.info('Text extraction results look good. All assertions passed.')

        request_id = self.client.schedule_data_extraction_task(
            fn,
            call_back_url=self.call_back_url,
            call_back_additional_info='hello world',
            doc_language='en',
            log_extra={'hello': 'world', 'test': True},
            output_format=OutputFormat.msgpack)
        self.srv.wait_for_test_results(timeout_sec=120,
                                       assert_func=assert_func,
                                       assert_func_args=[request_id])

        # the following additionally tests if we are able to delete directories
        self.client.delete_data_extraction_task_files(request_id)
