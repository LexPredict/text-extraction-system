import logging
import os
import unittest

import pikepdf
from text_extraction_system_api.client import TextExtractionSystemWebClient
from text_extraction_system_api.dto import RequestStatus, PlainTextStructure, OutputFormat

from integration_tests.call_back_server import DocumentCallbackServer
from integration_tests.testing_config import test_settings

log = logging.getLogger(__name__)


class TestDifferentLanguagesOCRExtract(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TextExtractionSystemWebClient(test_settings.api_url)
        self.srv = DocumentCallbackServer()
        self.call_back_url = f'http://{self.srv.bind_host}:{self.srv.bind_port}'

    def test_basic_api_call_back_with_2_languages_document(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'two_langs.pdf')

        def assert_func(rs_id: str):
            rs: RequestStatus = self.client.get_data_extraction_task_status(rs_id)
            assert rs.status == 'DONE'
            assert os.path.basename(fn) == rs.original_file_name
            assert rs.converted_cleaned_pdf is False
            assert rs.tables_extracted is False
            assert rs.plain_text_extracted
            assert rs.text_structure_extracted

            text = self.client.get_plain_text(rs.request_id)
            with self.client.get_pdf_as_local_file(rs.request_id) as tfn:
                with pikepdf.open(tfn) as pdf:
                    assert len(pdf.pages) == 1

            text_struct: PlainTextStructure = self.client.get_extracted_text_structure_as_msgpack(
                rs.request_id)
            assert text_struct.language in ('en', 'ru')
            if text_struct.language == 'en':
                assert 'This is top secret' in text
                assert 'Top.' in text
                assert 'являлся Тор.' not in text
            elif text_struct.language == 'ru':
                assert 'This is top secret' not in text
                assert 'Top.' not in text
                assert 'являлся Тор.' in text
            assert len(text_struct.pages) == 1
            assert 3 > len(text_struct.paragraphs) > 0
            for i in text_struct.paragraphs:
                assert i.language == text_struct.language
            assert len(text_struct.sentences) == 3
            for i in text_struct.sentences:
                assert i.language == text_struct.language
            log.info('Text extraction results look good. All assertions passed.')

        for lang in ('en', 'ru'):
            request_id = self.client.schedule_data_extraction_task(
                fn,
                call_back_url=self.call_back_url,
                call_back_additional_info='hello world',
                doc_language=lang,
                log_extra={'hello': 'world', 'test': True},
                output_format=OutputFormat.msgpack)
            self.srv.wait_for_test_results(timeout_sec=120,
                                           assert_func=assert_func,
                                           assert_func_args=[request_id])

            # the following additionally tests if we are able to delete directories
            self.client.delete_data_extraction_task_files(request_id)
