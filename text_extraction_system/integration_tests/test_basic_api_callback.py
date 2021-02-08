import logging
import os

import pikepdf
from pandas import DataFrame

from text_extraction_system_api.client import TextExtractionSystemWebClient
from text_extraction_system_api.dto import RequestStatus, PlainTextStructure, TableList, DataFrameTableList
from .call_back_server import DocumentCallbackServer
from .testing_config import test_settings

log = logging.getLogger(__name__)


def test_basic_api_call_back():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'many_pages.odt')
    client = TextExtractionSystemWebClient(test_settings.api_url)

    def assert_func(rfile, headers):
        log.info('Text extraction results are ready...')
        rs: RequestStatus = RequestStatus.from_json(rfile)
        assert rs.status == 'DONE'
        assert os.path.basename(fn) == rs.original_file_name
        assert rs.converted_cleaned_pdf
        assert rs.tables_extracted is False
        assert rs.plain_text_extracted
        assert rs.plain_text_structure_extracted
        assert rs.additional_info == 'hello world'

        text = client.get_plain_text(rs.request_id)
        for i in range(1, 22):
            assert f'This is page {i}' in text

        with client.get_pdf_as_local_file(rs.request_id) as tfn:
            with pikepdf.open(tfn) as pdf:
                assert len(pdf.pages) == 22

        text_struct: PlainTextStructure = client.get_plain_text_structure(rs.request_id)
        assert text_struct.language == 'en'
        assert len(text_struct.pages) == 22
        assert len(text_struct.paragraphs) > 1
        assert len(text_struct.sentences) > 2

        log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)

    request_id = client.schedule_data_extraction_task(fn,
                                                      call_back_url=f'http://{srv.bind_host}:{srv.bind_port}',
                                                      call_back_additional_info='hello world',
                                                      log_extra={'hello': 'world', 'test': True})
    srv.wait_for_test_results(120)

    # the following additionally tests if we are able to delete directories
    client.delete_data_extraction_task_files(request_id)


def test_basic_api_call_back_tables():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'tables.pdf')
    client = TextExtractionSystemWebClient(test_settings.api_url)

    def assert_func(rfile, headers):
        log.info('Text extraction results are ready...')
        rs: RequestStatus = RequestStatus.from_json(rfile)
        assert rs.status == 'DONE'
        assert os.path.basename(fn) == rs.original_file_name
        assert rs.converted_cleaned_pdf is True
        assert rs.searchable_pdf_created
        assert rs.pdf_pages_ocred == [2]
        assert rs.tables_extracted
        assert rs.plain_text_extracted
        assert rs.plain_text_structure_extracted

        table_list_json: TableList = client.get_tables_json(rs.request_id)
        assert len(table_list_json.tables) == 6

        table_list_df: DataFrameTableList = client.get_tables_df(rs.request_id)

        # Table on page 3 was originally an image. Testing tesseract with this.
        assert table_list_df.tables[-1].page == 3
        assert isinstance(table_list_df.tables[-1].df, DataFrame)

        log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)
    client.schedule_data_extraction_task(fn,
                                         call_back_url=f'http://{srv.bind_host}:{srv.bind_port}',
                                         call_back_additional_info='hello world')

    srv.wait_for_test_results(60)


def test_basic_api_call_back_ocr():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'ocr1.pdf')
    client = TextExtractionSystemWebClient(test_settings.api_url)

    def assert_func(rfile, headers):
        log.info('Text extraction results are ready...')
        rs: RequestStatus = RequestStatus.from_json(rfile)
        assert rs.status == 'DONE'
        assert os.path.basename(fn) == rs.original_file_name
        assert rs.converted_cleaned_pdf
        assert rs.pdf_pages_ocred
        assert rs.searchable_pdf_created
        log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)

    client.schedule_data_extraction_task(fn,
                                         call_back_url=f'http://{srv.bind_host}:{srv.bind_port}',
                                         call_back_additional_info='hello world',
                                         log_extra={'hello': 'world', 'test': True})
    srv.wait_for_test_results(60)


def test_basic_api_call_back_errors():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'not_pdf.pdf')
    client = TextExtractionSystemWebClient(test_settings.api_url)

    def assert_func(rfile, headers):
        log.info('Text extraction results are ready...')
        rs: RequestStatus = RequestStatus.from_json(rfile)
        assert rs.status == 'FAILURE'
        log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)

    client.schedule_data_extraction_task(fn,
                                         call_back_url=f'http://{srv.bind_host}:{srv.bind_port}',
                                         call_back_additional_info='hello world',
                                         log_extra={'hello': 'world', 'test': True})
    srv.wait_for_test_results(60)


def test_basic_api_call_back_cancel():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'ocr1.pdf')
    client = TextExtractionSystemWebClient(test_settings.api_url)

    def assert_func(rfile, headers):
        raise Exception('Results are unexpected. We tried to cancel the task.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)

    request_id = client.schedule_data_extraction_task(fn,
                                                      call_back_url=f'http://{srv.bind_host}:{srv.bind_port}',
                                                      call_back_additional_info='hello world',
                                                      log_extra={'hello': 'world', 'test': True})

    from time import sleep
    sleep(10)
    del_res = client.cancel_data_extraction_task(request_id)
    assert del_res.task_ids
    assert del_res.successfully_revoked
    assert not del_res.problems

    try:
        srv.wait_for_test_results(15)
    except TimeoutError:
        pass


def test_eternal_recursion():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'recursion1.pdf')
    client = TextExtractionSystemWebClient(test_settings.api_url)

    def assert_func(rfile, headers):
        log.info('Text extraction results are ready...')
        rs: RequestStatus = RequestStatus.from_json(rfile)
        assert rs.status != 'FAILURE'
        log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)

    client.schedule_data_extraction_task(fn,
                                         call_back_url=f'http://{srv.bind_host}:{srv.bind_port}',
                                         call_back_additional_info='hello world',
                                         log_extra={'hello': 'world', 'test': True})
    srv.wait_for_test_results(600)


def test_proper_page_merge_in():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'apache2_license_partially_images.odt')
    client = TextExtractionSystemWebClient(test_settings.api_url)

    def assert_func(rfile, headers):
        log.info('Text extraction results are ready...')
        rs: RequestStatus = RequestStatus.from_json(rfile)
        assert rs.status == 'DONE'
        assert os.path.basename(fn) == rs.original_file_name
        assert rs.converted_cleaned_pdf
        assert rs.plain_text_extracted
        assert rs.plain_text_structure_extracted
        assert rs.additional_info == 'hello world'

        text = client.get_plain_text(rs.request_id)
        text_struct: PlainTextStructure = client.get_plain_text_structure(rs.request_id)
        assert len(text_struct.pages) == 4
        assert 'REPRODUCTION, AND DISTRIBUTION' in text  # page 1
        assert 'subsequently incorporated' in text  # page 2
        assert 'conditions stated in this License. ' in text  # page 3
        assert 'See the License for the specific language governing' in text  # page 4

        log.info('Text extraction results look good. All assertions passed.')

    srv = DocumentCallbackServer(bind_host=test_settings.call_back_server_bind_host,
                                 bind_port=test_settings.call_back_server_bind_port,
                                 test_func=assert_func)

    client.schedule_data_extraction_task(fn,
                                         call_back_url=f'http://{srv.bind_host}:{srv.bind_port}',
                                         call_back_additional_info='hello world',
                                         log_extra={'hello': 'world', 'test': True})
    srv.wait_for_test_results(120)
