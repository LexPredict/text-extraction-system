import logging
import os
import unittest
from contextlib import closing
from unittest import mock
from zipfile import ZipFile

import pikepdf
import pytest
from requests import HTTPError

from text_extraction_system_api.client import TextExtractionSystemWebClient
from .testing_config import test_settings

log = logging.getLogger(__name__)


class TestBasicSynchronousAPIMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TextExtractionSystemWebClient(test_settings.api_url)
        self.fn = os.path.join(os.path.dirname(__file__), 'data', 'many_pages.odt')

    def test_basic_api_extract_plain_text_from_document(self):
        resp = self.client.extract_plain_text_from_document(self.fn)
        for i in range(1, 22):
            assert f'This is page {i}' in resp

    def test_rotated_page_with_small_amount_of_text(self):
        self.fn = os.path.join(os.path.dirname(__file__), 'data', 'finstat90_rotation_set.pdf')
        resp = self.client.extract_plain_text_from_document(self.fn, doc_language='en')
        assert 'financial statements' in resp.lower()

    def test_basic_api_extract_plain_text_from_document_expired(self):
        exception = HTTPError(mock.Mock(status=504), "Input file is too big")
        with pytest.raises(HTTPError) as error_info:
            with self.client.extract_plain_text_from_document(self.fn, full_extract_timeout_sec=2):
                assert error_info == exception

    def test_extract_text_from_document_and_generate_searchable_pdf_as_local_file(self):
        resp = self.client.extract_text_from_document_and_generate_searchable_pdf_as_local_file(
            self.fn)
        with resp as tfn:
            with pikepdf.open(tfn) as pdf:
                assert len(pdf.pages) == 22

    def test_extract_text_from_document_and_generate_searchable_pdf_as_local_file_expired(self):
        exception = HTTPError(mock.Mock(status=504), "Input file is too big")
        with pytest.raises(HTTPError) as error_info:
            with self.client.extract_text_from_document_and_generate_searchable_pdf_as_local_file(
                    self.fn, full_extract_timeout_sec=2):
                assert error_info == exception

    def test_extract_all_data_from_document(self):
        resp = self.client.extract_all_data_from_document(self.fn)
        with resp as tfn:
            with closing(ZipFile(tfn)) as archive:
                assert len(archive.infolist()) == 5

    def test_extract_all_data_from_document_expired(self):
        exception = HTTPError(mock.Mock(status=504), "Input file is too big")
        with pytest.raises(HTTPError) as error_info:
            with self.client.extract_all_data_from_document(self.fn, full_extract_timeout_sec=2):
                assert error_info == exception
