import logging
import os

import pikepdf
from text_extraction_system_api.client import TextExtractionSystemWebClient
from text_extraction_system_api.dto import RequestStatus, PlainTextStructure, OutputFormat

from integration_tests.call_back_server import DocumentCallbackServer
from integration_tests.testing_config import test_settings

log = logging.getLogger(__name__)


def test_basic_api_call_back_with_2_languages_document():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'two_langs.pdf')
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

        text = client.get_plain_text(rs.request_id)

        with client.get_pdf_as_local_file(rs.request_id) as tfn:
            with pikepdf.open(tfn) as pdf:
                assert len(pdf.pages) == 1

        text_struct: PlainTextStructure = client.get_extracted_text_structure_as_msgpack(rs.request_id)
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
        assert len(text_struct.paragraphs) == 1
        for i in text_struct.paragraphs:
            assert i.language == text_struct.language
        assert len(text_struct.sentences) == 3
        for i in text_struct.sentences:
            assert i.language == text_struct.language

        log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)

    for lang in ('en', 'ru'):
        request_id = client.schedule_data_extraction_task(fn,
                                                          call_back_url=f'http://{srv.bind_host}:{srv.bind_port}',
                                                          call_back_additional_info='hello world',
                                                          doc_language=lang,
                                                          log_extra={'hello': 'world', 'test': True},
                                                          output_format=OutputFormat.msgpack)
        srv.wait_for_test_results(120)

        # the following additionally tests if we are able to delete directories
        client.delete_data_extraction_task_files(request_id)
