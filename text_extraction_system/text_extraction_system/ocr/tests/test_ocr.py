import os

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract.data_extract import extract_text_pdfminer, extract_text_and_structure
from text_extraction_system.ocr.ocr import ocr_page_to_pdf, orientation_and_script_detected
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


def test_image_contains_text1():
    fn = os.path.join(data_dir, 'deskew_goes_crazy.png')
    assert orientation_and_script_detected(fn)


def test_image_contains_text2():
    fn = os.path.join(data_dir, 'picture_angles__00002.png')
    assert not orientation_and_script_detected(fn)


def test_image_contains_text3():
    fn = os.path.join(data_dir, 'multi_angle_multi_lang.png')
    assert not orientation_and_script_detected(fn)


def test_image_contains_text4():
    fn = os.path.join(data_dir, 'picture_angles__00003.png')
    assert not orientation_and_script_detected(fn)


def test_image_contains_text5():
    fn = os.path.join(data_dir, 'realdoc__00121.png')
    assert orientation_and_script_detected(fn)
