import logging
import os
import unittest

import pikepdf

from text_extraction_system_api.client import TextExtractionSystemWebClient
from text_extraction_system_api.dto import RequestStatus, PlainTextStructure, TableList, \
    OutputFormat

from integration_tests.call_back_server import DocumentCallbackServer
from integration_tests.testing_config import test_settings

log = logging.getLogger(__name__)


class TestBasicAPICallbackMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TextExtractionSystemWebClient(test_settings.api_url)
        self.srv = DocumentCallbackServer()
        self.call_back_url = f'http://{self.srv.bind_host}:{self.srv.bind_port}'

    def test_basic_api_call_back(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'many_pages.odt')

        def assert_func(rs_id: str):
            rs: RequestStatus = self.client.get_data_extraction_task_status(rs_id)
            assert rs.status == 'DONE'
            assert os.path.basename(fn) == rs.original_file_name
            assert rs.converted_cleaned_pdf
            assert rs.tables_extracted is False
            assert rs.plain_text_extracted
            assert rs.text_structure_extracted
            assert rs.additional_info == 'hello world'

            text = self.client.get_plain_text(rs.request_id)
            for i in range(1, 22):
                assert f'This is page {i}' in text

            with self.client.get_pdf_as_local_file(rs.request_id) as tfn:
                with pikepdf.open(tfn) as pdf:
                    assert len(pdf.pages) == 22

            text_struct: PlainTextStructure = self.client.get_extracted_text_structure_as_msgpack(
                rs.request_id)
            assert text_struct.language == 'en'
            assert len(text_struct.pages) == 22
            assert len(text_struct.paragraphs) == 1
            assert len(text_struct.sentences) > 2

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

    def test_basic_api_call_back_tables_msgpack(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'tables.pdf')

        def assert_func(rs_id: str):
            rs: RequestStatus = self.client.get_data_extraction_task_status(rs_id)
            assert rs.status == 'DONE'
            assert os.path.basename(fn) == rs.original_file_name
            assert rs.converted_cleaned_pdf is False
            assert rs.searchable_pdf_created
            assert rs.tables_extracted
            assert rs.plain_text_extracted
            assert rs.text_structure_extracted

            table_list_json: TableList = self.client.get_extracted_tables_as_msgpack(rs.request_id)
            assert len(table_list_json.tables) == 6

            log.info('Text extraction results look good. All assertions passed.')

        request_id = self.client.schedule_data_extraction_task(
            fn,
            doc_language='en',
            call_back_url=self.call_back_url,
            call_back_additional_info='hello world',
            output_format=OutputFormat.msgpack)
        self.srv.wait_for_test_results(timeout_sec=60,
                                       assert_func=assert_func,
                                       assert_func_args=[request_id])

    # ToDo: fix TableDetector bugs and uncomment this test
    # def test_basic_api_call_back_tables_disabled_msgpack(self):
    #     fn = os.path.join(os.path.dirname(__file__), 'data', 'tables.pdf')
    #
    #     def assert_func(rs_id: str):
    #         rs: RequestStatus = self.client.get_data_extraction_task_status(rs_id)
    #         assert rs.status == 'DONE'
    #         assert os.path.basename(fn) == rs.original_file_name
    #         assert rs.converted_cleaned_pdf is False
    #         assert rs.searchable_pdf_created
    #         assert not rs.tables_extracted
    #         assert rs.plain_text_extracted
    #         assert rs.text_structure_extracted
    #
    #         log.info('Text extraction results look good. All assertions passed.')
    #
    #     request_id = self.client.schedule_data_extraction_task(
    #         fn,
    #         call_back_url=self.call_back_url,
    #         call_back_additional_info='hello world',
    #         table_extraction_enable=False,
    #         output_format=OutputFormat.msgpack)
    #     self.srv.wait_for_test_results(timeout_sec=60,
    #                                    assert_func=assert_func,
    #                                    assert_func_args=[request_id])

    # ToDo: fix TableDetector bugs and uncomment this test
    # def test_basic_api_call_back_tables_json(self):
    #     fn = os.path.join(os.path.dirname(__file__), 'data', 'tables.pdf')
    #
    #     def assert_func(rs_id: str):
    #         rs: RequestStatus = self.client.get_data_extraction_task_status(rs_id)
    #         assert rs.status == 'DONE'
    #         assert os.path.basename(fn) == rs.original_file_name
    #         assert rs.converted_cleaned_pdf is False
    #         assert rs.searchable_pdf_created
    #         assert rs.tables_extracted
    #         assert rs.plain_text_extracted
    #         assert rs.text_structure_extracted
    #
    #         table_list_json: TableList = self.client.get_extracted_tables_as_json(rs.request_id)
    #         assert len(table_list_json.tables) == 6
    #
    #         log.info('Text extraction results look good. All assertions passed.')
    #
    #     request_id = self.client.schedule_data_extraction_task(
    #         fn,
    #         call_back_url=self.call_back_url,
    #         call_back_additional_info='hello world',
    #         output_format=OutputFormat.json)
    #     self.srv.wait_for_test_results(timeout_sec=60,
    #                                    assert_func=assert_func,
    #                                    assert_func_args=[request_id])

    def test_basic_api_call_back_ocr(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'ocr1.pdf')

        def assert_func(rs_id: str):
            rs: RequestStatus = self.client.get_data_extraction_task_status(rs_id)
            assert rs.status == 'DONE'
            assert os.path.basename(fn) == rs.original_file_name
            assert rs.pdf_pages_ocred
            assert rs.searchable_pdf_created
            log.info('Text extraction results look good. All assertions passed.')

        request_id = self.client.schedule_data_extraction_task(
            fn,
            call_back_url=self.call_back_url,
            call_back_additional_info='hello world',
            log_extra={'hello': 'world', 'test': True})
        self.srv.wait_for_test_results(timeout_sec=60,
                                       assert_func=assert_func,
                                       assert_func_args=[request_id])

    def test_basic_api_call_back_errors(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'not_pdf.pdf')

        def assert_func(rs_id: str):
            rs: RequestStatus = self.client.get_data_extraction_task_status(rs_id)
            assert rs.status == 'FAILURE'
            log.info('Text extraction results look good. All assertions passed.')

        request_id = self.client.schedule_data_extraction_task(
            fn,
            call_back_url=self.call_back_url,
            call_back_additional_info='hello world',
            log_extra={'hello': 'world', 'test': True})
        self.srv.wait_for_test_results(timeout_sec=60,
                                       assert_func=assert_func,
                                       assert_func_args=[request_id])

    def test_basic_api_call_back_cancel(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'ocr1.pdf')

        def assert_func():
            raise Exception('Results are unexpected. We tried to cancel the task.')

        request_id = self.client.schedule_data_extraction_task(
            fn,
            call_back_url=self.call_back_url,
            call_back_additional_info='hello world',
            log_extra={'hello': 'world', 'test': True})

        from time import sleep
        sleep(10)
        del_res = self.client.purge_data_extraction_task(request_id)
        assert del_res.task_ids
        assert del_res.successfully_revoked
        assert not del_res.problems

        try:
            self.srv.wait_for_test_results(timeout_sec=15,
                                           assert_func=assert_func,
                                           assert_func_args=[])
        except TimeoutError:
            pass

    def test_proper_page_merge_in(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'apache2_license_partially_images.odt')

        def assert_func(rs_id: str):
            rs: RequestStatus = self.client.get_data_extraction_task_status(rs_id)
            assert rs.status == 'DONE'
            assert os.path.basename(fn) == rs.original_file_name
            assert rs.converted_cleaned_pdf
            assert rs.plain_text_extracted
            assert rs.text_structure_extracted
            assert rs.additional_info == 'hello world'

            text = self.client.get_plain_text(rs.request_id)
            text_struct: PlainTextStructure = self.client.get_extracted_text_structure_as_msgpack(
                rs.request_id)
            assert len(text_struct.pages) == 4
            assert 'REPRODUCTION, AND DISTRIBUTION' in text  # page 1
            assert 'subsequently incorporated' in text  # page 2
            assert 'conditions stated in this License.' in text  # page 3
            assert 'See the License for the specific language governing' in text  # page 4

            log.info('Text extraction results look good. All assertions passed.')

        request_id = self.client.schedule_data_extraction_task(
            fn,
            doc_language='en',
            call_back_url=self.call_back_url,
            call_back_additional_info='hello world',
            log_extra={'hello': 'world', 'test': True},
            output_format=OutputFormat.msgpack)
        self.srv.wait_for_test_results(timeout_sec=120,
                                       assert_func=assert_func,
                                       assert_func_args=[request_id])
