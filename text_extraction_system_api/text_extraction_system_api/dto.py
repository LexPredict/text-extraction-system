from dataclasses import dataclass
from typing import List, Optional, Dict

from dataclasses_json import dataclass_json
from pandas import DataFrame
from pydantic.dataclasses import dataclass as pydantic_dataclass

STATUS_PENDING = 'PENDING'
STATUS_DONE = 'DONE'
STATUS_FAILURE = 'FAILURE'


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
    converted_to_pdf: bool = False
    searchable_pdf_created: bool = False
    pdf_pages_ocred: Optional[List[int]] = None
    plain_text_extracted: bool = False
    plain_text_structure_extracted: bool = False
    tables_extracted: bool = False
    additional_info: Optional[str] = None


@pydantic_dataclass
@dataclass_json
@dataclass
class PlainTextPage:
    number: int
    start: int
    end: int


@pydantic_dataclass
@dataclass_json
@dataclass
class PlainTextSection:
    start: int
    end: int
    title: str
    title_start: int
    title_end: int
    level: int
    abs_level: int


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
class PlainTextStructure:
    title: str
    language: str
    pages: List[PlainTextPage]
    sentences: List[PlainTextSentence]
    paragraphs: List[PlainTextParagraph]
    sections: List[PlainTextSection]


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


@dataclass
class DataFrameTableList:
    tables: List[DataFrameTable]


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
