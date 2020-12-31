from dataclasses import dataclass
from typing import List

from camelot.core import Table as CamelotTable


@dataclass
class PDFPagePreProcessResults:
    """
    Contains everything we can safely extract from a single PDF page.
    May be built either from the initial iteration of over the original/converted PDF document
    or from the OCR-ed PDF pages in parallel sub-tasks.
    """
    page_num: int
    page_plain_text: str
    camelot_tables: List[CamelotTable]
