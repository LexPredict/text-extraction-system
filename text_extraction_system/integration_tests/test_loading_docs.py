import logging
import os
import unittest
import zipfile
from shutil import rmtree, copyfileobj
from tempfile import mkdtemp

from text_extraction_system_api.client import TextExtractionSystemWebClient
from text_extraction_system_api.dto import RequestStatus

from .testing_config import test_settings

log = logging.getLogger(__name__)


class TestLoading2ndTime(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TextExtractionSystemWebClient(test_settings.api_url)

    def test_extract_text_rotated4(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'pdf_img_90.pdf')
        temp_dir = mkdtemp()
        try:
            pdf_1st = os.path.join(temp_dir, '1st_time.pdf')
            with self.client.extract_all_data_from_document(
                    fn, char_coords_debug_enable=True) as zip_fn:
                with zipfile.ZipFile(zip_fn, 'r') as archive:
                    with archive.open('pdf_img_90.ocred_corr.pdf', 'r') as pdf_processed:
                        with open(pdf_1st, 'bw') as f_pdf_1st:
                            copyfileobj(pdf_processed, f_pdf_1st)

            with self.client.extract_all_data_from_document(
                    pdf_1st, char_coords_debug_enable=True) as zip_fn:
                with zipfile.ZipFile(zip_fn, 'r') as archive:
                    with archive.open('1st_time.plain.txt', 'r') as f_txt:
                        txt = f_txt.read().decode('utf-8')
                        assert txt.count('Vertical text') == 77
        finally:
            rmtree(temp_dir)


class TestLoadingRotatedDocs(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TextExtractionSystemWebClient(test_settings.api_url)

    def test_extract_text_rotated1(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'rotated1.pdf.tiff')
        text = self.client.extract_plain_text_from_document(fn)
        expected = '''certain angle '''
        assert expected in text

    def test_extract_text_rotated2(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'rotated_small_angle.pdf.tiff')
        text = self.client.extract_plain_text_from_document(fn, doc_language='en')
        expected = '''d at a certain angle 1. This is a text rotated at a certain angle 2. This is a text
    a text rotated at a certain angle 4. This is a text rotated at a
    dat a certain angle 6. This is a text rotated at a certain angle 7.
    
    his is a text rotate
    rotated at a certain angle 3. This is
    certain angle 5. This is a text rotate'''
        assert expected in text

    def test_extract_text_rotated4(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'two_vertical_lines.png')
        with self.client.extract_all_data_from_document(fn) as zip_fn:
            with zipfile.ZipFile(zip_fn, 'r') as archive:
                with archive.open('status.json', 'r') as status_f:
                    req_status: RequestStatus = RequestStatus.from_json(status_f.read())
                    # it should not be rotated because tesseract can't detect any script on it
                    assert not req_status.page_rotate_angles[0]

    def test_extract_text_rotated6(self):
        fn = os.path.join(os.path.dirname(__file__), 'data', 'album_90.pdf')
        with self.client.extract_all_data_from_document(fn, doc_language='en') as zip_fn:
            with zipfile.ZipFile(zip_fn, 'r') as archive:
                with archive.open('status.json', 'r') as status_f:
                    s = status_f.read()
                    req_status: RequestStatus = RequestStatus.from_json(s)
                    assert req_status.page_rotate_angles[0] == 90
                with archive.open('album_90.plain.txt', 'r') as txt_f:
                    txt = txt_f.read().decode('utf-8')
                    assert 'This text was vertical but' in txt
