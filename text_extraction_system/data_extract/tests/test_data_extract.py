import csv
import os
from io import StringIO

from lxml import etree

from text_extraction_system.commons.tests.commons import default_settings
from text_extraction_system.data_extract.data_extract import tika_extract_xhtml, get_tables_from_pdf_tabula, \
    get_tables_from_pdf_camelot

data_dir = os.path.join(os.path.dirname(__file__), 'data')


def test_tika_returns_coords_in_cdata():
    with default_settings():
        fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
        text: str = tika_extract_xhtml(fn)
        root = etree.fromstring(text.encode('utf-8'))
        pdf_coords = root[-1][-1]
        f = StringIO(pdf_coords.text)
        assert len(pdf_coords.text) > 0
        reader = csv.reader(f, delimiter=',')
        i: int = 0
        for row in reader:
            assert len(row) == 4
            for coord in row:
                try:
                    float(coord)
                except ValueError as ve:
                    raise Exception(f'Can not convert coordinate to float at line {i}:\n{row}') from ve
            i += 1


def test_table_extraction_tabula1():
    pdf_fn = os.path.join(data_dir, 'tables.pdf')
    tables = get_tables_from_pdf_tabula(pdf_fn)

    print(tables)


def test_table_extraction_camelot1():
    pdf_fn = os.path.join(data_dir, 'tables.pdf')
    tables = get_tables_from_pdf_camelot(pdf_fn)

    print(tables)
