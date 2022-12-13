import os

import pikepdf

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract.data_extract import extract_text_pdfminer
from text_extraction_system.pdf.pdf import split_pdf_to_page_blocks, extract_page_images, iterate_pages, \
    page_requires_ocr

data_dir = os.path.join(os.path.dirname(__file__), 'data')


def test_pdf_requires_ocr1():
    fn = os.path.join(data_dir, 'ocr1.pdf')
    pages = [page_num for page_num, page in enumerate(iterate_pages(fn)) if page_requires_ocr(page)]
    assert pages == [1, 2]


def test_pdf_requires_ocr2():
    fn = os.path.join(data_dir, 'pdf_complicated.pdf')
    pages = [page_num for page_num, page in enumerate(iterate_pages(fn)) if page_requires_ocr(page)]
    assert not pages


@with_default_settings
def test_extract_images():
    fn = os.path.join(data_dir, 'ocr1.pdf')
    dirs_to_be_deleted = set()
    with extract_page_images(fn) as images:
        for page, image in enumerate(images):
            assert os.path.getsize(image) > 5
            assert os.path.splitext(image)[1] == '.png'
            dirs_to_be_deleted.add(os.path.dirname(image))
    for d in dirs_to_be_deleted:
        assert not os.path.exists(d)


def test_split_pdf1():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    with split_pdf_to_page_blocks(fn, 3) as block_files:
        assert len(block_files) == 3
        for fn in block_files:
            with pikepdf.open(fn) as pdf:
                assert len(pdf.pages) == 3


def test_split_pdf2():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    with split_pdf_to_page_blocks(fn, 4) as block_files:
        assert len(block_files) == 3
        with pikepdf.open(block_files[0]) as pdf:
            assert len(pdf.pages) == 4
        with pikepdf.open(block_files[1]) as pdf:
            assert len(pdf.pages) == 4
        with pikepdf.open(block_files[2]) as pdf:
            assert len(pdf.pages) == 1


def test_split_pdf_text():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    with split_pdf_to_page_blocks(fn, 4) as block_files:
        txt1 = str(extract_text_pdfminer(block_files[0]))
        txt2 = str(extract_text_pdfminer(block_files[1]))
        txt3 = str(extract_text_pdfminer(block_files[2]))
        assert 'This is page 1.' in txt1
        assert 'This is page 2.' in txt1
        assert 'This is page 3.' in txt1
        assert 'This is page 4.' in txt1
        assert 'This is page 5.' in txt2
        assert 'This is page 6.' in txt2
        assert 'This is page 7.' in txt2
        assert 'This is page 8.' in txt2
        assert 'This is page 9.' in txt3

        assert 'This is page 1.' not in txt2
        assert 'This is page 2.' not in txt3
        assert 'This is page 3.' not in txt2
        assert 'This is page 4.' not in txt3
        assert 'This is page 5.' not in txt1
        assert 'This is page 6.' not in txt3
        assert 'This is page 7.' not in txt1
        assert 'This is page 8.' not in txt3
        assert 'This is page 9.' not in txt2

        assert len(block_files) == 3


def test_split_pdf_file_names1():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    with split_pdf_to_page_blocks(fn, 4) as block_files:
        assert os.path.basename(block_files[0]) == 'pdf_9_pages_0001_0004.pdf'
        assert os.path.basename(block_files[1]) == 'pdf_9_pages_0005_0008.pdf'
        assert os.path.basename(block_files[2]) == 'pdf_9_pages_0009.pdf'


def test_split_pdf_file_names2():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    with split_pdf_to_page_blocks(fn, 3) as block_files:
        assert os.path.basename(block_files[0]) == 'pdf_9_pages_0001_0003.pdf'
        assert os.path.basename(block_files[1]) == 'pdf_9_pages_0004_0006.pdf'
        assert os.path.basename(block_files[2]) == 'pdf_9_pages_0007_0009.pdf'


def test_split_pdf_file_names3():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    with split_pdf_to_page_blocks(fn, 1) as block_files:
        assert os.path.basename(block_files[0]) == 'pdf_9_pages_0001.pdf'
        assert os.path.basename(block_files[1]) == 'pdf_9_pages_0002.pdf'
        assert os.path.basename(block_files[-1]) == 'pdf_9_pages_0009.pdf'


def test_split_pdf_file_names4():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    with split_pdf_to_page_blocks(fn, 11) as block_files:
        assert len(block_files) == 1
        assert block_files[0].endswith('pdf_9_pages.pdf')


def test_split_pdf_file_names5():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    with split_pdf_to_page_blocks(fn, 3, page_block_base_name='qwerty.pdf') as block_files:
        assert os.path.basename(block_files[0]) == 'qwerty_0001_0003.pdf'
        assert os.path.basename(block_files[1]) == 'qwerty_0004_0006.pdf'
        assert os.path.basename(block_files[2]) == 'qwerty_0007_0009.pdf'


def test_split_pdf_file_names6():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    with split_pdf_to_page_blocks(fn, 11, page_block_base_name='aaa.pdf') as block_files:
        assert len(block_files) == 1
        assert os.path.basename(block_files[0]) == 'pdf_9_pages.pdf'
