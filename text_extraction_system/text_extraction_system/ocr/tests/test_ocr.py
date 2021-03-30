import os

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract.data_extract import extract_text_pdfminer, extract_text_and_structure
from text_extraction_system.ocr.ocr import ocr_page_to_pdf
from text_extraction_system.pdf.pdf import extract_page_images, extract_page_ocr_images

data_dir = os.path.join(os.path.dirname(__file__), 'data')


@with_default_settings
def test_ocr_page():
    fn = os.path.join(data_dir, 'ocr1.pdf')
    txt = ''
    with extract_page_images(fn) as image_fns:
        for image in image_fns:
            with ocr_page_to_pdf(image) as pdf_fn:
                txt += '\n' + extract_text_pdfminer(pdf_fn)
    txt = txt.replace('  ', ' ')
    assert 'each Contributor hereby grants to You' in txt
    assert 'You may add Your own' in txt
    assert 'Submission of Contributions' in txt
    assert 'END OF TERMS AND CONDITIONS' in txt


@with_default_settings
def test_ocr_blurry():
    fn = os.path.join(data_dir, 'blurred_noisy_scan.pdf')
    txt = ''
    with extract_page_ocr_images(fn, 1, 1) as image_fns:
        image_with_text, image_no_text = image_fns[0]
        with ocr_page_to_pdf(image_with_text) as pdf_fn:
            txt += '\n' + extract_text_pdfminer(pdf_fn)
    assert 'Approved  For  Release' in txt


@with_default_settings
def test_ocr_rotated():
    fn = os.path.join(data_dir, 'rotated1.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        with ocr_page_to_pdf(png_fns[0]) as pdf_fn:
            txt, txt_struct = extract_text_and_structure(pdf_fn)
    assert 'rotated' in txt


@with_default_settings
def test_ocr_rotated_small_angle():
    fn = os.path.join(data_dir, 'rotated_small_angle.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        with ocr_page_to_pdf(png_fns[0]) as pdf_fn:
            txt, txt_struct = extract_text_and_structure(pdf_fn)
    assert 'rotated' in txt
