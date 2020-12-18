import os
from dataclasses import dataclass
from io import StringIO
from logging import getLogger
from typing import List

import camelot
import tabula
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


def get_text_of_pdf_pdfminer(pdf_fn: str) -> str:
    output_string = StringIO()
    with open(pdf_fn, 'rb') as in_file:
        parser = PDFParser(in_file)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.create_pages(doc):
            interpreter.process_page(page)
    return output_string.getvalue()


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


def get_tables_from_pdf_camelot(pdf_fn: str) -> List[Table]:
    tables = camelot.read_pdf(pdf_fn, pages='all')
    return tables


def get_tables_from_pdf_tabula(pdf_fn: str) -> List[Table]:
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


def tika_extract_xhtml(src_fn: str) -> str:
    conf: Settings = get_settings()

    encoding_name = 'utf-8'
    os.environ['LEXNLP_TIKA_PARSER_MODE'] = 'pdf_only'
    # other possible values are 'coords_embedded' and ''
    os.environ['LEXNLP_TIKA_XML_DETAIL'] = 'coords_flat'

    cmd = ['java',
           '-cp',
           f'{conf.tika_jar_path}/*',
           '-Dsun.java2d.cmm=sun.java2d.cmm.kcms.KcmsServiceProvider',
           'org.apache.tika.cli.TikaCLI',
           f'--config={conf.tika_config}',
           '-x',
           f'-e{encoding_name}',
           src_fn]

    def err(line):
        log.error(f'TIKA parsing {src_fn}:\n{line}')

    return read_output(cmd, stderr_callback=err,
                       encoding=encoding_name,
                       timeout_sec=60 * 20) or ''
