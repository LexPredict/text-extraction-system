import os

from text_extraction_system.data_extract.data_extract import get_text_of_pdf_pdfminer
from text_extraction_system.ocr.ocr import ocr_page_to_pdf
from text_extraction_system.pdf.pdf import extract_page_images

data_dir = os.path.join(os.path.dirname(__file__), 'data')


def test_ocr_page():
    fn = os.path.join(data_dir, 'ocr1.pdf')
    txt = ''
    for page, image in extract_page_images(fn, [1, 2]):
        with ocr_page_to_pdf(image) as pdf_fn:
            txt += '\n' + get_text_of_pdf_pdfminer(pdf_fn)
    txt = txt.replace('  ', ' ')
    assert 'each Contributor hereby grants to You' in txt
    assert 'You may add Your own' in txt
    assert 'Submission of Contributions' in txt
    assert 'END OF TERMS AND CONDITIONS' in txt
