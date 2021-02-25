import os
from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract.data_extract import get_first_page_layout
from text_extraction_system.pdf.pdf import extract_page_images, calc_covers

data_dir = os.path.join(os.path.dirname(__file__), 'data')


@with_default_settings
def test_calc_covers_vector_image():
    # this file is a one-page PDF with a relatively large image
    # but the image is a vector (LTCurve, LTLine etc)
    file_path = os.path.join(data_dir, 're_ocr_page_3.pdf')

    with extract_page_images(file_path, start_page=1, end_page=1, pdf_password='') as image_fns:
        with open(file_path, 'rb') as in_file:
            page_layout = get_first_page_layout(in_file)
            tc, ic = calc_covers(page_layout)
            assert ic == 0
            assert tc > 0


@with_default_settings
def test_calc_covers_bitmap():
    file_path = os.path.join(data_dir, 'one_page_big_bitmap.pdf')

    with extract_page_images(file_path, start_page=1, end_page=1, pdf_password='') as image_fns:
        with open(file_path, 'rb') as in_file:
            page_layout = get_first_page_layout(in_file)
            tc, ic = calc_covers(page_layout)
            assert ic > 0
            assert tc > 0

            # I measured visual size of image and text in a graphic editor
            vis_im_size = 772 * 509
            vis_text_size = 772 * 128
            vis_ratio = vis_im_size / vis_text_size

            calc_ratio = ic / tc
            diff = abs(vis_ratio - calc_ratio) / vis_ratio
            assert diff < 0.1
