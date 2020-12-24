import re
from dataclasses import dataclass
from io import StringIO
from logging import getLogger
from typing import List, Tuple

from dataclasses_json import dataclass_json
from lexnlp.nlp.en.segments.paragraphs import get_paragraphs
from lexnlp.nlp.en.segments.sections import get_document_sections_with_titles
from lexnlp.nlp.en.segments.sentences import pre_process_document, get_sentence_span_list
from pdfminer import utils as pdfminer_utils
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.layout import LTImage, LTTextBox, LTContainer, LTText
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

log = getLogger(__name__)
REG_EXTRA_SPACE = re.compile(r'<[\s/]*(?:[A-Za-z]+|[Hh]\d)[\s/]*>|\x00')


@dataclass_json
@dataclass
class PlainTextPage:
    number: int
    start: int
    end: int


@dataclass_json
@dataclass
class PlainTextSection:
    title: str
    start: int
    end: int


@dataclass_json
@dataclass
class PlainTextSpan:
    start: int
    end: int


@dataclass_json
@dataclass
class PlainTextStructure:
    pages: List[PlainTextPage]
    sentences: List[PlainTextSpan]
    paragraphs: List[PlainTextSpan]
    sections: List[PlainTextSection]


def find_pages(s: str, sep: str) -> List[PlainTextPage]:
    cur_page_start = 0
    cur_page_num = 1

    res = list()

    next_sep_pos = s.find(sep)
    while next_sep_pos != -1:
        cur_page_end = next_sep_pos + len(sep)
        res.append(PlainTextPage(number=cur_page_num,
                                 start=cur_page_start,
                                 end=cur_page_end))
        cur_page_start = cur_page_end
        cur_page_num += 1
        next_sep_pos = s.find(sep, cur_page_start)

    return res


class TextAndStructureConverter(TextConverter):

    def __init__(self, rsrcmgr, outfp, codec='utf-8', pageno=1, laparams=None, showpageno=False, imagewriter=None):
        super().__init__(rsrcmgr, outfp, codec, pageno, laparams, showpageno, imagewriter)

    def write_text(self, text):
        text = pdfminer_utils.compatible_encode_method(text, self.codec, 'ignore')
        if self.outfp_binary:
            text = text.encode()
        self.outfp.write(text)
        return

    def render(self, item, dst: StringIO):
        if isinstance(item, LTContainer):
            for child in item:
                self.render(child, dst)
        elif isinstance(item, LTText):
            dst.write(item.get_text())
        if isinstance(item, LTTextBox):
            dst.write('\n')
        elif isinstance(item, LTImage):
            pass

    def receive_layout(self, ltpage):
        page_io = StringIO()
        self.render(ltpage, page_io)
        page_str = page_io.getvalue()
        pre_process_document(page_str)
        page_str = REG_EXTRA_SPACE.sub('', page_str)
        page_str = page_str.replace('\r\n', '\n')
        self.write_text(page_str)
        self.write_text('\f')
        return


def extract_text_and_structure(pdf_fn: str) -> Tuple[str, PlainTextStructure]:
    output_string = StringIO()
    with open(pdf_fn, 'rb') as in_file:
        parser = PDFParser(in_file)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        device = TextAndStructureConverter(rsrcmgr, output_string, laparams=LAParams())
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.create_pages(doc):
            interpreter.process_page(page)
    text: str = output_string.getvalue()

    # See TextConverter sources - it adds \f in the end of each page.
    pages = find_pages(text, '\f')

    sentence_spans = get_sentence_span_list(text)
    sentences = [PlainTextSpan(sp[0], sp[1]) for sp in sentence_spans]

    # There was a try-except in Contraxsuite catching some lexnlp exception.
    # Not putting it here because it should be solved on lexnlp side.
    paragraphs = [PlainTextSpan(sp[0], sp[1]) for sp in get_paragraphs(text, return_spans=True)]

    sections = [PlainTextSection(title=sp['title'], start=sp['start'], end=sp['end'])
                for sp in get_document_sections_with_titles(text, sentence_list=sentence_spans)]

    return text, PlainTextStructure(pages=pages, sentences=sentences, paragraphs=paragraphs, sections=sections)


def extract_text_pdfminer(pdf_fn: str) -> str:
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
