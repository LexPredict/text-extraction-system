from logging import getLogger
from subprocess import CalledProcessError
from typing import List, Tuple

import camelot
import tabula
from camelot.core import Table as CamelotTable, TableList as CamelotTableList

from text_extraction_system_api.dto import Rectangle, Table, DataFrameTable, TableList, DataFrameTableList

log = getLogger(__name__)


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


def get_tables_from_pdf_camelot_dataframes(pdf_fn: str, accuracy_threshold: float = 50) -> Tuple[TableList,
                                                                                                 DataFrameTableList]:
    tables: CamelotTableList = camelot.read_pdf(pdf_fn, pages='all')
    df_table_data = [
        DataFrameTable(
            df=t.df,
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
    return TableList(tables=table_data), DataFrameTableList(tables=df_table_data)


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
