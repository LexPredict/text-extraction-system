import logging
import os

from text_extraction_system_api.client import TextExtractionSystemWebClient
from .testing_config import test_settings

log = logging.getLogger(__name__)


def test_extract_text_rotated1():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'rotated1.pdf.tiff')
    client = TextExtractionSystemWebClient(test_settings.api_url)
    text = client.extract_plain_text_from_document(fn)
    expected = '''is a text rotated at a certain angle 1. This is a text rotated at a certain angle 2. This is a text 
otated at a certain angle 3. This is a text rotated at a certain angle 4. This is a text rotated at a 
ertain angle 5. This is a text rotated at a certain angle 6. This is a text rotated at a certain angle 7.'''
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
    fn = os.path.join(os.path.dirname(__file__), 'data', 'picture_angles__00003.png')
    client = TextExtractionSystemWebClient(test_settings.api_url)
    text = client.extract_plain_text_from_document(fn)
    assert not text.strip()
