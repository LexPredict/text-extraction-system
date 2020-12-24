import os
from dataclasses import dataclass
from io import StringIO
from logging import getLogger
from subprocess import CalledProcessError
from typing import List

import camelot
import tabula
from camelot.core import Table as CamelotTable, TableList as CamelotTableList
from dataclasses_json import dataclass_json
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

from text_extraction_system.config import get_settings, Settings
from text_extraction_system.processes import read_output

log = getLogger(__name__)


@dataclass_json
@dataclass
class Rectangle:
    left: float
    top: float
    width: float
    height: float


@dataclass_json
@dataclass
class Table:
    coordinates: Rectangle
    data: List[List[str]]
    page: int = None


def get_tables_from_pdf_camelot(pdf_fn: str, accuracy_threshold: float = 50) -> List[Table]:
    tables: CamelotTableList = camelot.read_pdf(pdf_fn, pages='all')
    table_data = [
        Table(
            data=t.data,
            coordinates=Rectangle(
                left=t.cells[0][0].x1,
                top=t.cells[0][0].y1,
                width=t.cells[-1][-1].x2 - t.cells[0][0].x1,
                height=t.cells[0][0].y2 - t.cells[-1][-1].y1
            ),
            page=t.page
        ) for t in tables  # type: CamelotTable
        if t.accuracy > accuracy_threshold and len(t.cells) > 0 and len(t.cells[0]) > 0
    ]
    return table_data


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
