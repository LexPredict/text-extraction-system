import shutil

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract.data_extract import extract_text_and_structure
from text_extraction_system.ocr.ocr import ocr_page_to_pdf
from text_extraction_system.pdf.pdf import extract_page_images


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
    from text_extraction_system.pdf.pdf import extract_page_images, merge_pdf_pages
    from text_extraction_system.ocr.ocr import deskew, ocr_page_to_pdf
    import shutil
    orig_pdf_fn = '/home/mikhail/lexpredict/misc/angles/realdoc.pdf'
    with extract_page_images(orig_pdf_fn, 1, 1) as images:
        with deskew(images[0]) as (did_deskew, angle, rotated_or_original_image_fn):
            with ocr_page_to_pdf(rotated_or_original_image_fn, glyphless_text_only=True) as ocred_page_pdf:
                with merge_pdf_pages(orig_pdf_fn,
                                     single_page_merge_num_file_rotate=(1,
                                                                        ocred_page_pdf,
                                                                        angle if did_deskew else None)) as final_pdf:
                    shutil.copy(final_pdf, '/home/mikhail/lexpredict/misc/angles/processed_real_doc.pdf')


p2()
