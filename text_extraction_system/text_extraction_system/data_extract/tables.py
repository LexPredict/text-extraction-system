from logging import getLogger
from typing import Iterable

from camelot.core import Table as CamelotTable
from text_extraction_system_api.dto import Rectangle, Table, TableList

log = getLogger(__name__)


def get_table_dtos_from_camelot_output(camelot_tables: Iterable[CamelotTable],
                                       accuracy_threshold: float = 50) -> TableList:
    camelot_tables = list(camelot_tables)

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
        ) for t in camelot_tables  # type: CamelotTable
        if t.accuracy > accuracy_threshold and len(t.cells) > 0 and len(t.cells[0]) > 0
    ]
    return TableList(tables=table_data)
