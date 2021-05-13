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
    orig_pdf_fn = '/home/mikhail/lexpredict/misc/angles/A2A3E26061E43CD60156598713530D98C.pdf'
    page = 1

    with split_pdf_to_page_blocks(orig_pdf_fn) as page_fns:
        page_fn = page_fns[49]
        with extract_page_ocr_images(page_fn, 1, 1, dpi=300) as images:
            with ocr_page_to_pdf(images.get(1),
                                 glyphless_text_only=True,
                                 tesseract_page_orientation_detection=True) as ocred_page_pdf:  # type: str
                with merge_pdf_pages(orig_pdf_fn, single_page_merge_num_file_rotate=(1, ocred_page_pdf, None)) as final_pdf:
                    shutil.copy(page_fn, '/home/mikhail/lexpredict/misc/angles/A2A3E26061E43CD60156598713530D98C__00050.ocred.pdf')


#p2()

@with_default_settings
def p3():
    from text_extraction_system.data_extract.camelot.camelot import extract_tables_from_pdf_file
    dtos = extract_tables_from_pdf_file('/home/mikhail/lexpredict/misc/tables/problem1.pdf')
    print(len(dtos))

p3()