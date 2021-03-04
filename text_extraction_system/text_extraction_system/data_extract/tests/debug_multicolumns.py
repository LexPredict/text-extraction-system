import os
from typing import List

from text_extraction_system.commons.tests.commons import default_settings
from text_extraction_system.data_extract.camelot.camelot import extract_tables_borderless, CamelotTable
from text_extraction_system.data_extract.data_extract import get_first_page_layout

pdf_fn = os.path.join(os.path.dirname(__file__), 'data', '2columns.pdf')

with default_settings():
    with open(pdf_fn, 'rb') as in_file:
        page_layout = get_first_page_layout(in_file)
        tables: List[CamelotTable] = extract_tables_borderless(1, page_layout)
        for table in tables:
            for row in table.cells:
                for cell in row:
                    print(f'({cell.x1}; {cell.y1}; {cell.x2}; {cell.y2})\n{cell.text}\n-----\n')
