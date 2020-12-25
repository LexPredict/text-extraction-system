from dataclasses import dataclass
from typing import List, Optional

from dataclasses_json import dataclass_json
from pandas import DataFrame
from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass
@dataclass_json
@dataclass
class RequestStatus:
    request_id: str
    status: str
    converted_to_pdf: bool
    searchable_pdf_created: bool
    pdf_pages_ocred: List[int]
    plain_text_extracted: bool
    plain_text_structure_extracted: bool
    tables_extracted: bool


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
