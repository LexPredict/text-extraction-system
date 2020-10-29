import os
import shutil
import tempfile

import pikepdf
import textract

from text_extraction_system.pdf_util import split_pdf_to_page_blocks, join_pdf_blocks

data_dir = os.path.join(os.path.dirname(__file__), 'data')


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
        txt1 = str(textract.process(block_files[0]))
        txt2 = str(textract.process(block_files[1]))
        txt3 = str(textract.process(block_files[2]))

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
        assert block_files[0][-8:] == '_0_3.pdf'
        assert block_files[1][-8:] == '_4_7.pdf'
        assert block_files[2][-6:] == '_8.pdf'
    finally:
        shutil.rmtree(temp_dir)


def test_split_pdf_file_names2():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 3)
        assert block_files[0][-8:] == '_0_2.pdf'
        assert block_files[1][-8:] == '_3_5.pdf'
        assert block_files[2][-8:] == '_6_8.pdf'
    finally:
        shutil.rmtree(temp_dir)


def test_split_pdf_file_names3():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    temp_dir = tempfile.mkdtemp()
    try:
        block_files = split_pdf_to_page_blocks(fn, temp_dir, 1)
        assert block_files[0][-6:] == '_0.pdf'
        assert block_files[1][-6:] == '_1.pdf'
        assert block_files[-1][-6:] == '_8.pdf'
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
            txt = str(textract.process(dst_fn))
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
            txt = str(textract.process(dst_fn))
            for i in range(1, 9):
                assert f'This is page {i}.' in txt

        finally:
            os.remove(dst_fn)

    finally:
        shutil.rmtree(temp_dir)
