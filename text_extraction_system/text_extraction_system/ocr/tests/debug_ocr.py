import shutil

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract.data_extract import extract_text_and_structure
from text_extraction_system.ocr.ocr import ocr_page_to_pdf
from text_extraction_system.pdf.pdf import extract_page_images, extract_page_ocr_images


@with_default_settings
def p():
    fn = '..'
    with extract_page_images(fn, 54, 54) as image_fns:
        for image_fn in image_fns:
            shutil.copy(image_fn, '..')
            with ocr_page_to_pdf(image_fn) as page_pdf_fn:
                shutil.copy(page_pdf_fn, '..')
                text, struct = extract_text_and_structure(page_pdf_fn)
                # assert '...' in text


@with_default_settings
def p2():
    from text_extraction_system.pdf.pdf import merge_pdf_pages, split_pdf_to_page_blocks
    from text_extraction_system.ocr.ocr import ocr_page_to_pdf
    import shutil
    orig_pdf_fn = '/home/mikhail/Downloads/Archive_AOL_License_Example_orig.pdf'
    page = 1

    #with split_pdf_to_page_blocks(orig_pdf_fn) as page_fns:
    #    pass

    with extract_page_ocr_images(orig_pdf_fn, page, page, dpi=300) as images:
        with ocr_page_to_pdf(images.get(1),
                             glyphless_text_only=True,
                             tesseract_page_orientation_detection=True) as ocred_page_pdf:  # type: str
            with merge_pdf_pages(orig_pdf_fn, single_page_merge_num_file_rotate=(1, ocred_page_pdf, None)) as final_pdf:
                shutil.copy(final_pdf, '/home/mikhail/lexpredict/misc/angles/house_0003.ocred.pdf')


p2()
