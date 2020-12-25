import os
from typing import Callable

import pikepdf
import pytest

from text_extraction_system.data_extract.plain_text import extract_text_pdfminer
from text_extraction_system.pdf.convert_to_pdf import convert_to_pdf, InputFileDoesNotExist

data_dir = os.path.join(os.path.dirname(__file__), 'data')


def check_pdf_conversion(src_doc_fn: str, assert_pdf_by_fn_func: Callable[[str, ], None] = None):
    with convert_to_pdf(src_doc_fn) as pdf_temp_file:
        assert os.path.getsize(pdf_temp_file) > 100
        with open(pdf_temp_file, 'rb') as f:
            pdf_contents = f.read()
            # print(pdf_contents)
            assert b'%PDF' in pdf_contents and b'%%EOF' in pdf_contents
        if assert_pdf_by_fn_func is not None:
            assert_pdf_by_fn_func(pdf_temp_file)
    assert not os.path.exists(pdf_temp_file)
    assert not os.path.exists(os.path.dirname(pdf_temp_file))


def test_input_does_not_exist():
    def assert_pdf(fn: str):
        pass

    with pytest.raises(InputFileDoesNotExist):
        check_pdf_conversion(os.path.join(data_dir, 'wrong_file'), assert_pdf)


def test_basic_conversion():
    check_pdf_conversion(__file__)


def test_xlsx():
    def assert_pdf(fn: str):
        txt = extract_text_pdfminer(fn)
        # xlsx -> pdf conversion for the document which do not fit on the pages
        # goes not so good but at least all the text should be kept
        assert txt.count('fitting') == 144  # just counted them in the original xlsx

    check_pdf_conversion(os.path.join(data_dir, 'document1.xlsx'), assert_pdf)


def test_docx():
    def assert_pdf(fn: str):
        txt = extract_text_pdfminer(fn)
        assert txt.count('document') == 105
        with pikepdf.open(fn) as pdf:
            assert len(pdf.pages) == 3

    check_pdf_conversion(os.path.join(data_dir, 'docx_test.docx'), assert_pdf)


def test_doc():
    def assert_pdf(fn: str):
        txt = extract_text_pdfminer(fn)
        assert txt.count('This') == 104
        with pikepdf.open(fn) as pdf:
            assert len(pdf.pages) == 2

    check_pdf_conversion(os.path.join(data_dir, 'doc_test.doc'), assert_pdf)


def test_odf():
    def assert_pdf(fn: str):
        txt = extract_text_pdfminer(fn)
        assert txt.count('document') == 110
        with pikepdf.open(fn) as pdf:
            assert len(pdf.pages) == 3

    check_pdf_conversion(os.path.join(data_dir, 'odt_test.odt'), assert_pdf)


def test_tiff():
    def assert_pdf(fn: str):
        with pikepdf.open(fn) as pdf:
            assert len(pdf.pages) == 3

    check_pdf_conversion(os.path.join(data_dir, 'tiff_test.tiff'), assert_pdf)
