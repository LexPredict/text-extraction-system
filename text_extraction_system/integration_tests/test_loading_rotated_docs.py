import logging
import os
import zipfile

from text_extraction_system_api.client import TextExtractionSystemWebClient
from text_extraction_system_api.dto import RequestStatus
from .testing_config import test_settings

log = logging.getLogger(__name__)


def test_extract_text_rotated1():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'rotated1.pdf.tiff')
    client = TextExtractionSystemWebClient(test_settings.api_url)
    text = client.extract_plain_text_from_document(fn)
    expected = '''This is a text rotated at a certain angle 1. This is a text rotated at a certain angle 2. This is a text 
rotated at a certain angle 3. This is a text rotated at a certain angle 4. This is a text rotated at a 
certain angle 5. This is a text rotated at a certain angle 6. This is a text rotated at a certain angle 7.'''
    assert expected in text


def test_extract_text_rotated2():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'rotated_small_angle.pdf.tiff')
    client = TextExtractionSystemWebClient(test_settings.api_url)
    text = client.extract_plain_text_from_document(fn)
    expected = '''his is a text rotated at a certain angle 1. This is a text rotated at a certain angle 2. This is a text 
rotated at a certain angle 3. This is a text rotated at a certain angle 4. This is a text rotated at a 
certain angle 5. This is a text rotated at a certain angle 6. This is a text rotated at a certain angle 7.'''
    assert expected in text


def test_extract_text_rotated3():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'wrong_angle1.pdf')
    client = TextExtractionSystemWebClient(test_settings.api_url)
    with client.extract_all_data_from_document(fn) as zip_fn:
        with zipfile.ZipFile(zip_fn, 'r') as archive:
            with archive.open('status.json', 'r') as status_f:
                s = status_f.read()
                req_status: RequestStatus = RequestStatus.from_json(s)
                assert req_status.page_rotate_angles is None or int(req_status.page_rotate_angles[1]) == 0


def test_extract_text_rotated4():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'two_vertical_lines.png')
    client = TextExtractionSystemWebClient(test_settings.api_url)
    with client.extract_all_data_from_document(fn) as zip_fn:
        with zipfile.ZipFile(zip_fn, 'r') as archive:
            with archive.open('status.json', 'r') as status_f:
                s = status_f.read()
                req_status: RequestStatus = RequestStatus.from_json(s)
                # it should not be rotated because tesseract can't detect any script on it
                assert req_status.page_rotate_angles is None


def test_no_script_mistake1():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'mistake_no_text1.pdf')
    client = TextExtractionSystemWebClient(test_settings.api_url)
    text = client.extract_plain_text_from_document(fn)
    expected = '''Approvals and Licenses'''
    assert expected in text
