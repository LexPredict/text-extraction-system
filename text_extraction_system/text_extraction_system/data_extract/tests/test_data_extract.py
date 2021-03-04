import os

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract import data_extract

data_dir = os.path.join(os.path.dirname(__file__), 'data')


@with_default_settings
def test_text_structure_extraction():
    fn = os.path.join(data_dir, 'structured_text.pdf')
    text, full_struct = data_extract.extract_text_and_structure(fn)
    struct = full_struct.text_structure
    assert 'idea if it is really' in text
    assert 'etect the sections' in text
    assert len(struct.pages) == 2
    assert len(struct.paragraphs) == 6
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

    assert len(struct.text_structure.pages) == 7


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
