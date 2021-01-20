import shutil

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.pdf.pdf import extract_page_images
from text_extraction_system.ocr.ocr import ocr_page_to_pdf
from text_extraction_system.data_extract.data_extract import extract_text_and_structure_from_file


@with_default_settings
def p():
    fn = '...'
    with extract_page_images(fn, 1, 1) as image_fns:
        for image_fn in image_fns:
            shutil.copy(image_fn, '...')
            with ocr_page_to_pdf(image_fn) as page_pdf_fn:
                shutil.copy(page_pdf_fn, '...')
                text, struct = extract_text_and_structure_from_file(page_pdf_fn)
                assert '...' in text


p()
