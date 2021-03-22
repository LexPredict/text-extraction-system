import os
import warnings
from unittest.mock import MagicMock

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract import data_extract
from text_extraction_system.data_extract.tables import extract_tables
from text_extraction_system.pdf.pdf import extract_page_images

data_dir = os.path.join(os.path.dirname(__file__), 'data')


@with_default_settings
def test_text_structure_extraction():
    fn = os.path.join(data_dir, 'structured_text.pdf')
    text, full_struct = data_extract.extract_text_and_structure(fn)
    struct = full_struct.text_structure
    assert 'idea if it is really' in text
    assert 'etect the sections' in text
    assert len(struct.pages) == 2
    assert len(struct.paragraphs) == 5
    assert len(struct.sentences) == 15

    # should be 2 sections but its a problem of lexnlp
    assert len(struct.sections) == 3


@with_default_settings
def test_recursion1():
    from text_extraction_system.commons.sysutils import increase_recursion_limit
    increase_recursion_limit()
    fn = os.path.join(data_dir, 'recursion1.pdf')
    text, struct = data_extract.extract_text_and_structure(fn)
    assert len(struct.text_structure.pages) > 2


@with_default_settings
def test_recursion3():
    fn = os.path.join(data_dir, 'recursion3.png')

    from text_extraction_system.ocr.ocr import ocr_page_to_pdf

    with ocr_page_to_pdf(fn) as pdf_fn:
        text, struct = data_extract.extract_text_and_structure(pdf_fn)

    for num, page in enumerate(struct.text_structure.pages):
        assert num == page.number

    assert len(struct.text_structure.pages) == 1


@with_default_settings
def test_multicolumn_no_ocr():
    fn = os.path.join(data_dir, 'table-based-text_noocr.pdf')

    text, struct = data_extract.extract_text_and_structure(fn)

    s = '''Warren E. Agin, as Trustee of the bankruptcy estate of Variety Plus Real Estate Group, LLC (the “Debtor”) in 
Chapter 7 proceedings pending in the United States Bankruptcy Court for the District of Massachusetts (the 
“Bankruptcy Court”) as Case No. 19-11598 (the “Chapter 7 Case”), having an address at 50 Milk Street,16th 
Floor, Boston, MA 02109'''

    assert s in text


@with_default_settings
def test_multicolumn_ocr():
    fn = os.path.join(data_dir, 'table-based-text_scan.png')

    from text_extraction_system.ocr.ocr import ocr_page_to_pdf

    with ocr_page_to_pdf(fn) as pdf_fn:
        text, struct = data_extract.extract_text_and_structure(pdf_fn)

    # In fact for the OCR-ed multi-column text we extract the text wrong right now
    # because the OCR lib has no info in which order the text blocks should go.

    s = ''''''

    # assert s in text


@with_default_settings
def test_different_languages_extraction_with_no_ocr():
    fn = os.path.join(data_dir, 'two_langs_no_ocr.pdf')

    text, full_struct = data_extract.extract_text_and_structure(fn, language="en_US")
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


@with_default_settings
def test_table_warnings():
    fn = os.path.join(data_dir, 'camelot_warn.pdf')
    warn_mock = MagicMock('warn')
    warnings.warn = warn_mock

    with extract_page_images(fn, 1, 1) as image_fns:
        image_fn = image_fns[0]
        with open(fn, 'rb') as ocred_in_file:
            ocred_page_layout = data_extract.get_first_page_layout(ocred_in_file)
            camelot_tables = extract_tables(1, ocred_page_layout, image_fn)

        assert len(camelot_tables) == 1
    warn_mock.assert_not_called()
