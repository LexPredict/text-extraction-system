import os
import re
import shutil
import tempfile

import pikepdf

from text_extraction_system.data_extract.data_extract import get_text_of_pdf_pdfminer
from text_extraction_system.pdf.pdf import split_pdf_to_page_blocks, join_pdf_blocks, find_pages_requiring_ocr, \
    get_page_sequences, extract_page_images, merge_pfd_pages

data_dir = os.path.join(os.path.dirname(__file__), 'data')


def test_get_page_sequence1():
    actual = get_page_sequences([1, 2, 3, 4, 5])
    assert actual == [[1, 5]]


def test_get_page_sequence2():
    actual = get_page_sequences([2, 3, 4, 7, 8])
    assert actual == [[2, 4], [7, 8]]


def test_get_page_sequence3():
    actual = get_page_sequences([2, 3, 4, 8])
    assert actual == [[2, 4], [8, 8]]


def test_get_page_sequence4():
    actual = get_page_sequences([8, 2, 3, 4, 8, 8])
    assert actual == [[2, 4], [8, 8]]


def test_pdf_requires_ocr1():
    fn = os.path.join(data_dir, 'ocr1.pdf')
    pages = find_pages_requiring_ocr(fn)
    assert pages == [1, 2]


def test_pdf_requires_ocr2():
    fn = os.path.join(data_dir, 'pdf_complicated.pdf')
    pages = find_pages_requiring_ocr(fn)
    assert not pages


def test_extract_images():
    fn = os.path.join(data_dir, 'ocr1.pdf')
    dirs_to_be_deleted = list()
    pages_to_ocr = set()
    for page, image in extract_page_images(fn, [0, 2, 3]):
        assert os.path.getsize(image) > 5
        assert os.path.splitext(image)[1] == '.png'
        dirs_to_be_deleted.append(os.path.dirname(os.path.dirname(image)))
        pages_to_ocr.add(page)
    for d in dirs_to_be_deleted:
        assert not os.path.exists(d)
    assert pages_to_ocr == {0, 2, 3}


def test_split_pdf1():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 3)
        assert len(block_files) == 3
        for fn in block_files:
            with pikepdf.open(fn) as pdf:
                assert len(pdf.pages) == 3
    finally:
        shutil.rmtree(temp_dir)


def test_split_pdf2():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 4)
        assert len(block_files) == 3
        with pikepdf.open(block_files[0]) as pdf:
            assert len(pdf.pages) == 4
        with pikepdf.open(block_files[1]) as pdf:
            assert len(pdf.pages) == 4
        with pikepdf.open(block_files[2]) as pdf:
            assert len(pdf.pages) == 1
    finally:
        shutil.rmtree(temp_dir)


def test_split_pdf_text():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 4)
        txt1 = str(get_text_of_pdf_pdfminer(block_files[0]))
        txt2 = str(get_text_of_pdf_pdfminer(block_files[1]))
        txt3 = str(get_text_of_pdf_pdfminer(block_files[2]))

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
    finally:
        shutil.rmtree(temp_dir)


def test_split_pdf_file_names1():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 4)
        assert os.path.basename(block_files[0]) == 'pdf_9_pages_0001_0004.pdf'
        assert os.path.basename(block_files[1]) == 'pdf_9_pages_0005_0008.pdf'
        assert os.path.basename(block_files[2]) == 'pdf_9_pages_0009.pdf'
    finally:
        shutil.rmtree(temp_dir)


def test_split_pdf_file_names2():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 3)
        assert os.path.basename(block_files[0]) == 'pdf_9_pages_0001_0003.pdf'
        assert os.path.basename(block_files[1]) == 'pdf_9_pages_0004_0006.pdf'
        assert os.path.basename(block_files[2]) == 'pdf_9_pages_0007_0009.pdf'
    finally:
        shutil.rmtree(temp_dir)


def test_split_pdf_file_names3():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 1)
        assert os.path.basename(block_files[0]) == 'pdf_9_pages_0001.pdf'
        assert os.path.basename(block_files[1]) == 'pdf_9_pages_0002.pdf'
        assert os.path.basename(block_files[-1]) == 'pdf_9_pages_0009.pdf'
    finally:
        shutil.rmtree(temp_dir)


def test_split_pdf_file_names4():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 11)
        assert len(block_files) == 1
        assert block_files[0].endswith('pdf_9_pages.pdf')
    finally:
        shutil.rmtree(temp_dir)


def test_split_pdf_file_names5():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 3, page_block_base_name='qwerty.pdf')
        assert os.path.basename(block_files[0]) == 'qwerty_0001_0003.pdf'
        assert os.path.basename(block_files[1]) == 'qwerty_0004_0006.pdf'
        assert os.path.basename(block_files[2]) == 'qwerty_0007_0009.pdf'
    finally:
        shutil.rmtree(temp_dir)


def test_split_pdf_file_names6():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 11, page_block_base_name='aaa.pdf')
        assert len(block_files) == 1
        assert os.path.basename(block_files[0]) == 'aaa.pdf'
    finally:
        shutil.rmtree(temp_dir)


def test_join_pdfs1():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 4)

        dst_fn = tempfile.mktemp(suffix='.pdf')
        try:
            join_pdf_blocks(block_files, dst_fn)
            with pikepdf.open(dst_fn) as joined_pdf:
                assert len(joined_pdf.pages) == 9
            txt = str(get_text_of_pdf_pdfminer(dst_fn))
            for i in range(1, 9):
                assert f'This is page {i}.' in txt

        finally:
            os.remove(dst_fn)

    finally:
        shutil.rmtree(temp_dir)


def test_join_pdfs2():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = [fn]

        dst_fn = tempfile.mktemp(suffix='.pdf')
        try:
            join_pdf_blocks(block_files, dst_fn)
            with pikepdf.open(dst_fn) as joined_pdf:
                assert len(joined_pdf.pages) == 9
            txt = str(get_text_of_pdf_pdfminer(dst_fn))
            for i in range(1, 9):
                assert f'This is page {i}.' in txt

        finally:
            os.remove(dst_fn)

    finally:
        shutil.rmtree(temp_dir)


def test_merge_pdf_pages():
    orig_pdf = os.path.join(data_dir, 'pdf_text_4_pages.pdf')
    repl_pages = {1: os.path.join(data_dir, 'replacement_page.pdf'),
                  3: os.path.join(data_dir, 'smile.pdf')}
    should_be_deleted = list()
    with merge_pfd_pages(orig_pdf, repl_pages) as pdf_fn:
        should_be_deleted.append(pdf_fn)
        txt = get_text_of_pdf_pdfminer(pdf_fn)
    for fn in should_be_deleted:
        assert not os.path.isfile(fn)
        assert not os.path.isdir(os.path.dirname(fn))
    txt = re.sub(r'\s+', ' ', txt).strip()
    assert txt == 'This is page 1. Replacement page! This is page 3. This is an image!'
