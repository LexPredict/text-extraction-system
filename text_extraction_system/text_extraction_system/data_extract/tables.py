import shutil
import tempfile
from logging import getLogger
from subprocess import CalledProcessError
from typing import List, Tuple, Iterable

import tabula
from camelot.core import Table as CamelotTable
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams
from pdfminer.layout import LTPage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

from text_extraction_system.data_extract.camelot.camelot import extract_tables
from text_extraction_system.pdf.pdf import extract_all_page_images
from text_extraction_system_api.dto import Rectangle, Table, DataFrameTable, TableList, DataFrameTableList

log = getLogger(__name__)


def get_table_dtos_from_camelot_output(camelot_tables: Iterable[CamelotTable],
                                       accuracy_threshold: float = 50) -> Tuple[TableList,
                                                                                DataFrameTableList]:
    df_table_data = [
        DataFrameTable(
            df=t.df,
            coordinates=Rectangle(
                left=t.cells[0][0].x1,
                top=t.cells[0][0].y1,
                width=t.cells[-1][-1].x2 - t.cells[0][0].x1,
                height=t.cells[0][0].y2 - t.cells[-1][-1].y1
            ),
            page=t.page + 1
        ) for t in camelot_tables  # type: CamelotTable
        if t.accuracy > accuracy_threshold and len(t.cells) > 0 and len(t.cells[0]) > 0
    ]

    table_data = [
        Table(
            data=t.data,
            coordinates=Rectangle(
                left=t.cells[0][0].x1,
                top=t.cells[0][0].y1,
                width=t.cells[-1][-1].x2 - t.cells[0][0].x1,
                height=t.cells[0][0].y2 - t.cells[-1][-1].y1
            ),
            page=t.page + 1
        ) for t in camelot_tables  # type: CamelotTable
        if t.accuracy > accuracy_threshold and len(t.cells) > 0 and len(t.cells[0]) > 0
    ]
    return TableList(tables=table_data), DataFrameTableList(tables=df_table_data)


def get_tables_from_pdf_camelot_dataframes(pdf_fn: str, accuracy_threshold: float = 50) \
        -> Tuple[TableList, DataFrameTableList]:
    image_dir = tempfile.mkdtemp()
    try:
        with extract_all_page_images(pdf_fn) as page_images:
            tables: List[CamelotTable] = list()
            with open(pdf_fn, 'rb') as in_file:
                parser = PDFParser(in_file)
                doc = PDFDocument(parser)
                rsrcmgr = PDFResourceManager()
                laparams = LAParams()
                device = PDFPageAggregator(rsrcmgr, laparams=laparams)
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                page_num = 0
                for page in PDFPage.create_pages(doc):
                    interpreter.process_page(page)
                    page_layout: LTPage = device.get_result()
                    page_image_fn = page_images[page_num]
                    page_tables = extract_tables(page_num, page_layout, page_image_fn)
                    if page_tables:
                        tables.extend(page_tables)
                    page_num += 1

        return get_table_dtos_from_camelot_output(tables, accuracy_threshold)
    finally:
        shutil.rmtree(image_dir, ignore_errors=True)


def get_tables_from_pdf_tabula(pdf_fn: str) -> List[Table]:
    tables_data: List[Table] = list()

    # Tabula does not return the page number for the tables
    # when running with pages = 'all'.
    # So we iterate over the pages until it raises an error.
    p = 1
    while True:
        try:
            tables = tabula.read_pdf(
                pdf_fn,
                output_format='json',
                multiple_tables=True,
                pages=p)
            tt = [
                Table(
                    data=[[cell['text'] for cell in row] for row in table['data']],
                    coordinates=Rectangle(left=table['left'],
                                          top=table['top'],
                                          width=table['width'],
                                          height=table['height']),
                    page=p
                ) for table in tables
            ]
            tables_data += tt
            p += 1
        except CalledProcessError as err:
            if b'Page number does not exist' in err.stderr:
                break
            else:
                raise err

    return tables_data


def get_tables_from_pdf_tabula_no_page_nums(pdf_fn: str) -> List[Table]:
    # Tabula does not return the page number for the tables
    # when running with pages = 'all'.
    # This is a convenience method to return tables only without the page numbers or coordinates.
    tables = tabula.read_pdf(
        pdf_fn,
        output_format='json',
        multiple_tables=True,
        pages='all')
    tables_data = [
        Table(
            data=[[cell['text'] for cell in row] for row in table['data']],
            coordinates=Rectangle(left=table['left'],
                                  top=table['top'],
                                  width=table['width'],
                                  height=table['height'])
        ) for table in tables
    ]

    return tables_data
