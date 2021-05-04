import logging
import os
import zipfile
from shutil import rmtree, copyfileobj
from tempfile import mkdtemp

from text_extraction_system_api.client import TextExtractionSystemWebClient
from .testing_config import test_settings

log = logging.getLogger(__name__)


def test_extract_text_rotated4():
    fn = os.path.join(os.path.dirname(__file__), 'data', 'realdoc__00121_orig.pdf')
    client = TextExtractionSystemWebClient(test_settings.api_url)
    temp_dir = mkdtemp()
    try:
        pdf_1st = os.path.join(temp_dir, '1st_time.pdf')
        pdf_2nd = os.path.join(temp_dir, '2nd_time.pdf')
        with client.extract_all_data_from_document(fn, char_coords_debug_enable=True) as zip_fn:
            with zipfile.ZipFile(zip_fn, 'r') as archive:
                with archive.open('realdoc__00121_orig.ocred_corr.pdf', 'r') as pdf_processed:
                    with open(pdf_1st, 'bw') as f_pdf_1st:
                        copyfileobj(pdf_processed, f_pdf_1st)

        with client.extract_all_data_from_document(pdf_1st, char_coords_debug_enable=True) as zip_fn:
            with zipfile.ZipFile(zip_fn, 'r') as archive:
                with archive.open('1st_time_corr.pdf', 'r') as pdf_processed2:
                    with open(pdf_2nd, 'bw') as f_pdf_2nd:
                        with archive.open('1st_time.plain.txt', 'r') as f_txt:
                            txt = f_txt.read().decode('utf-8')
                            assert txt.count('Patient services is received') == 1
    finally:
        rmtree(temp_dir)
