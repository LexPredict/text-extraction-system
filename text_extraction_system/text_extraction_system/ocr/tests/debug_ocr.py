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
    from text_extraction_system.ocr.ocr import determine_skew, ocr_page_to_pdf, rotate_image
    import shutil
    orig_pdf_fn = '/home/mikhail/lexpredict/misc/angles/realdoc.pdf'
    page = 121
    with split_pdf_to_page_blocks(orig_pdf_fn, 1) as page_fns:
        shutil.copy(page_fns[page - 1], '/home/mikhail/lexpredict/misc/angles/realdoc__00121_orig.pdf')

    with extract_page_ocr_images(orig_pdf_fn, page, page, dpi=300) as images:
        angle = determine_skew(images[0][1], False)
        with rotate_image(images[0][1], angle, 300, align_to_closest_90=True) as rotated_or_original_image_fn:
            with ocr_page_to_pdf(rotated_or_original_image_fn,
                                 glyphless_text_only=True,
                                 tesseract_page_orientation_detection=True) as ocred_page_pdf:
                with merge_pdf_pages(orig_pdf_fn,
                                     single_page_merge_num_file_rotate=(page,
                                                                        ocred_page_pdf,
                                                                        angle)) as final_pdf:
                    with split_pdf_to_page_blocks(final_pdf, 1) as page_fns:
                        shutil.copy(page_fns[page - 1], '/home/mikhail/lexpredict/misc/angles/line_splitting.pdf')


p2()
