import csv
import os
from collections import defaultdict
from io import StringIO
from time import time

from lxml import etree

from text_extraction_system.commons.tests.commons import default_settings
from text_extraction_system.data_extract.tables import get_tables_from_pdf_tabula, get_tables_from_pdf_camelot, \
    get_tables_from_pdf_tabula_no_page_nums
from text_extraction_system.data_extract.tika import tika_extract_xhtml

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
    start = time()
    tables = get_tables_from_pdf_tabula(pdf_fn)
    t = time() - start
    tables_by_page = defaultdict(list)
    for tt in tables:
        tables_by_page[tt.page].append(tt)

    assert len(tables_by_page[1]) == 3
    assert len(tables_by_page[2]) == 2
    assert 3 not in tables_by_page
    assert len(tables_by_page[1][0].data) == 4
    assert len(tables_by_page[1][0].data[0]) == 4

    # tabula returns table coordinates not in standard pdf coordinate system
    # zero point in tabula is in top-left corner while in pdf standard it should be in bottom-left
    assert tables_by_page[1][0].coordinates.top < 150

    print(f'Tabula table extraction: {t:.3f} s')


def test_table_extraction_camelot1():
    pdf_fn = os.path.join(data_dir, 'tables.pdf')
    start = time()
    tables = get_tables_from_pdf_camelot(pdf_fn)
    t = time() - start
    tables_by_page = defaultdict(list)
    for tt in tables:
        tables_by_page[tt.page].append(tt)

    assert len(tables_by_page[1]) == 3
    assert len(tables_by_page[2]) == 2
    assert 3 not in tables_by_page
    assert len(tables_by_page[1][0].data) == 4
    assert len(tables_by_page[1][0].data[0]) == 4

    # camelot returns table coordinates in standard pdf coordinate system
    # zero point in is in bottom-left corner
    assert tables_by_page[1][0].coordinates.top > 700

    print(f'Camelot table extraction: {t:.3f} s')


def test_table_extraction_camelot2():
    # Camelot works much longer than tabula (in no-page-numbers mode).
    # This test takes 80+ seconds but it detects all tables as it should
    # (Tabula detects only the first one)
    # Disabling to speed up test run.
    return
    pdf_fn = os.path.join(data_dir, 'tables2.pdf')
    start = time()
    tables = get_tables_from_pdf_camelot(pdf_fn)
    t = time() - start
    assert len(tables) > 100
    assert tables[-1].page == 100
    print(f'Camelot table extraction: {t:.3f} s')


def test_table_extraction_tabula2():
    # Tabula detects only [['X', 'Y']] for the 100-page document tables2.pdf with a lot of small tables in it.
    return
    pdf_fn = os.path.join(data_dir, 'tables2.pdf')
    start = time()
    tables = get_tables_from_pdf_tabula_no_page_nums(pdf_fn)
    t = time() - start
    print(f'Tabula table extraction: {t:.3f} s')
