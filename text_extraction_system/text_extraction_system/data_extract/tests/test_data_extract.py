import os
import warnings
from unittest.mock import MagicMock

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract import data_extract
from text_extraction_system.data_extract.tables import extract_tables

data_dir = os.path.join(os.path.dirname(__file__), 'data')


@with_default_settings
def test_text_structure_extraction():
    fn = os.path.join(data_dir, 'structured_text.pdf')
    with data_extract.extract_text_and_structure(fn) as (text, full_struct, _a, _b):
        struct = full_struct.text_structure
        assert 'idea if it is really' in text
        assert 'etect the sections' in text
        assert len(struct.pages) == 2
        assert len(struct.paragraphs) == 5
        assert len(struct.sentences) == 15

        # should be 2 sections but its a problem of lexnlp
        assert len(struct.sections) == 3


@with_default_settings
def test_different_languages_extraction_with_no_ocr():
    fn = os.path.join(data_dir, 'two_langs_no_ocr.pdf')

    with data_extract.extract_text_and_structure(fn, language="en_US") as (text, full_struct, _a, _b):
        struct = full_struct.text_structure
        assert 'This is top secret' in text
        assert len(struct.pages) == 1
        assert len(struct.paragraphs) == 1
        for i in struct.paragraphs:
            assert i.language == struct.language
        assert len(struct.sentences) == 2
        for i in struct.sentences:
            assert i.language == struct.language


@with_default_settings
def test_table_ocr():
    fn = os.path.join(data_dir, 'table1.png')
    warn_mock = MagicMock('warn')
    warnings.warn = warn_mock

    from text_extraction_system.ocr.ocr import ocr_page_to_pdf

    with ocr_page_to_pdf(fn) as pdf_fn:
        with open(pdf_fn, 'rb') as ocred_in_file:
            ocred_page_layout = data_extract.get_first_page_layout(ocred_in_file)
            camelot_tables = extract_tables(1, ocred_page_layout, fn)

    assert len(camelot_tables) == 1
    warn_mock.assert_not_called()
