import datetime
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any

from dataclasses_json import dataclass_json
from pandas import DataFrame
from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

STATUS_PENDING = 'PENDING'
STATUS_DONE = 'DONE'
STATUS_FAILURE = 'FAILURE'


class OutputFormat(str, Enum):
    msgpack = 'msgpack'
    json = 'json'


@pydantic_dataclass
@dataclass_json
@dataclass
class TaskCancelResult:
    request_id: str
    task_ids: List[str]
    successfully_revoked: List[str]
    problems: Dict[str, str]


@pydantic_dataclass
@dataclass_json
@dataclass
class RequestStatus:
    request_id: str
    original_file_name: str
    status: str
    output_format: OutputFormat
    error_message: Optional[str] = None
    converted_cleaned_pdf: bool = False
    searchable_pdf_created: bool = False
    corrected_pdf_created: bool = False
    pdf_pages_ocred: Optional[List[int]] = None
    plain_text_extracted: bool = False
    text_structure_extracted: bool = False
    pdf_coordinates_extracted: bool = False
    tables_extracted: bool = False
    additional_info: Optional[str] = None
    page_rotate_angles: Optional[List[float]] = None


@pydantic_dataclass
@dataclass_json
@dataclass
class RequestStatuses:
    request_statuses: List[RequestStatus]


class UserRequestsQuery(BaseModel):
    request_ids: List[str]
    request_times: List[datetime.datetime]
    sort_column: str
    sort_order: str
    page_index: int
    records_on_page: int


@pydantic_dataclass
@dataclass_json
@dataclass
class UserRequestsSummary:
    request_statuses: List[RequestStatus]
    tasks_pending: int


@pydantic_dataclass
@dataclass_json
@dataclass
class PlainTextPage:
    number: int
    start: int
    end: int
    bbox: List[float]

    def to_dictionary(self) -> Dict[str, Any]:
        # returns: {'number': 0, 'start': 0, 'end': 1109,
        #            'bbox': [0.0, 0.0, 595.2999877929688, 841.8900146484375]}
        return {'number': self.number, 'start': self.start, 'end': self.end,
                'bbox': self.bbox}


@pydantic_dataclass
@dataclass_json
@dataclass
class PlainTextSection:
    start: int
    end: int
    title: Optional[str]
    title_start: Optional[int]
    title_end: Optional[int]
    level: int
    abs_level: int
    left: float
    top: float
    page: int


@pydantic_dataclass
@dataclass_json
@dataclass
class PlainTextSentence:
    start: int
    end: int
    language: str


@pydantic_dataclass
@dataclass_json
@dataclass
class PlainTextParagraph:
    start: int
    end: int
    language: str


@pydantic_dataclass
@dataclass_json
@dataclass
class PlainTextSentence:
    start: int
    end: int
    language: str


@pydantic_dataclass
@dataclass_json
@dataclass
class PlainTableOfContentsRecord:
    title: str
    level: int
    left: int
    top: int
    page: int


@pydantic_dataclass
@dataclass_json
@dataclass
class PlainTextStructure:
    title: Optional[str]
    language: str
    pages: List[PlainTextPage]
    sentences: List[PlainTextSentence]
    paragraphs: List[PlainTextParagraph]
    sections: List[PlainTextSection]
    table_of_contents: List[PlainTableOfContentsRecord]


@pydantic_dataclass
@dataclass_json
@dataclass
class PDFCoordinates:
    char_bboxes: List[List[float]]


@pydantic_dataclass
@dataclass_json
@dataclass
class TextAndPDFCoordinates:
    text_structure: PlainTextStructure
    pdf_coordinates: PDFCoordinates


@pydantic_dataclass
@dataclass_json
@dataclass
class Rectangle:
    left: float
    top: float
    width: float
    height: float


@pydantic_dataclass
@dataclass_json
@dataclass
class Table:
    coordinates: Rectangle
    data: List[List[str]]
    page: Optional[int] = None


@pydantic_dataclass
@dataclass_json
@dataclass
class TableList:
    tables: List[Table]


@dataclass
class DataFrameTable:
    coordinates: Rectangle
    df: DataFrame
    page: Optional[int] = None


@pydantic_dataclass
@dataclass_json
@dataclass
class SystemInfo:
    version_number: str
    git_branch: str
    git_commit: str
    lexnlp_git_branch: str
    lexnlp_git_commit: str
    build_date: str
    python_version: str
    pandas_version: str
