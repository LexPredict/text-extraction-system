import os
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from logging import getLogger
from subprocess import CompletedProcess, PIPE
from tempfile import mkdtemp
from typing import Tuple, Generator, Optional, Dict, Any, List

import msgpack
from lexnlp.nlp.en.segments.paragraphs import get_paragraphs
from lexnlp.nlp.en.segments.sections import get_document_sections_with_titles
from lexnlp.nlp.en.segments.sentences import get_sentence_span_list
from lexnlp.nlp.en.segments.titles import get_titles
from pdfminer.converter import PDFPageAggregator
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.layout import LTPage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from text_extraction_system_api.pdf_coordinates.pdf_coords_common import PdfMarkup

from text_extraction_system.config import get_settings
from text_extraction_system.data_extract.lang import get_lang_detector
from text_extraction_system.ocr.ocr import ocr_page_to_pdf
from text_extraction_system.pdf.pdf import extract_page_ocr_images, \
    raise_from_pdfbox_error_messages
from text_extraction_system.processes import raise_from_process
from text_extraction_system.utils import LanguageConverter
from text_extraction_system_api.dto import PlainTextParagraph, PlainTextSection, PlainTextPage, PlainTextStructure, \
    PlainTextSentence, TextAndPDFCoordinates, PDFCoordinates, PlainTableOfContentsRecord
from text_extraction_system_api.pdf_coordinates.pdf_coords_common import find_page_by_smb_index
from text_extraction_system_api.pdf_coordinates.coord_text_map import CoordTextMap

log = getLogger(__name__)
PAGE_SEPARATOR = '\n\n\f'
DPI: int = 300


@contextmanager
def extract_text_and_structure(pdf_fn: str,
                               pdf_password: str = None,
                               timeout_sec: int = 3600,
                               language: str = "",
                               correct_pdf: bool = False,
                               render_coords_debug: bool = False) \
        -> Tuple[
            str, TextAndPDFCoordinates, str, Dict[int, float]]:  # text, structure, corrected_pdf_fn, page_rotate_angles

    if render_coords_debug:
        correct_pdf = True

    java_modules_path = get_settings().java_modules_path

    # Convert language to language code
    lang_converter = LanguageConverter()
    language, locale_code = lang_converter.get_language_and_locale_code(language)

    temp_dir = mkdtemp(prefix='pdf_text_')
    out_fn = os.path.join(temp_dir, os.path.splitext(os.path.basename(pdf_fn))[0] + '.msgpack')
    out_pdf_fn = pdf_fn
    try:
        args = ['java', '-cp', f'{java_modules_path}/*',
                'com.lexpredict.textextraction.GetTextFromPDF',
                pdf_fn,
                out_fn,
                '-f', 'pages_msgpack']

        if pdf_password:
            args.append('-p')
            args.append(pdf_password)

        if correct_pdf:
            out_pdf_fn = os.path.join(temp_dir, os.path.splitext(os.path.basename(pdf_fn))[0] + '_corr.pdf')
            args.append('-corrected_output')
            args.append(out_pdf_fn)

            if render_coords_debug:
                args.append('-render_char_rects')

        completed_process: CompletedProcess = subprocess.run(args, check=False, timeout=timeout_sec,
                                                             universal_newlines=True, stderr=PIPE, stdout=PIPE)
        raise_from_process(log, completed_process, process_title=lambda: f'Extract text and structure from {pdf_fn}')

        raise_from_pdfbox_error_messages(completed_process)

        with open(out_fn, 'rb') as pages_f:
            # see object structure in com.lexpredict.textextraction.dto.PDFPlainText
            pdfbox_res: Dict[str, Any] = msgpack.unpack(pages_f, raw=False)

        # Remove Null characters because of incompatibility with PostgreSQL
        text = pdfbox_res['text'].replace("\x00", "")
        if len(text) == 0:
            pdf_coordinates = PDFCoordinates(char_bboxes=pdfbox_res['charBBoxes'])
            text_struct = PlainTextStructure(title='',
                                             language=language or 'en',  # FastText returns English for empty strings
                                             pages=[],
                                             sentences=[],
                                             paragraphs=[],
                                             sections=[],
                                             table_of_contents=[])
            yield text, \
                  TextAndPDFCoordinates(text_structure=text_struct, pdf_coordinates=pdf_coordinates), \
                  out_pdf_fn, \
                  None

            return

        page_rotate_angles: List[float] = [pdfpage['deskewAngle'] for pdfpage in pdfbox_res['pages']]

        pages = []
        num: int = 0
        for p in pdfbox_res['pages']:
            p_res = PlainTextPage(number=num, start=p['location'][0], end=p['location'][1], bbox=p['bbox'])
            pages.append(p_res)
            num += 1

        table_of_contents = []
        for p in pdfbox_res['tableOfContents']:
            tc = PlainTableOfContentsRecord(
                title=p['title'], level=p['level'], left=p['left'], top=p['top'], page=p['page'])
            table_of_contents.append(tc)

        sentence_spans = get_sentence_span_list(text)

        lang = get_lang_detector()

        sentences = [PlainTextSentence(start=start,
                                       end=end,
                                       language=language or lang.predict_lang(segment))
                     for start, end, segment in sentence_spans]

        # There was a try-except in Contraxsuite catching some lexnlp exception.
        # Not putting it here because it should be solved on lexnlp side.
        paragraphs = [PlainTextParagraph(start=start,
                                         end=end,
                                         language=language or lang.predict_lang(segment))
                      for segment, start, end in get_paragraphs(text, return_spans=True)]

        if table_of_contents:
            sections = get_sections_from_table_of_contents(table_of_contents,
                                                           pdfbox_res['charBBoxes'],
                                                           pages)
        else:
            sections = [PlainTextSection(title=sect.title,
                                         start=sect.start,
                                         end=sect.end,
                                         title_start=sect.title_start,
                                         title_end=sect.title_end,
                                         level=sect.level,
                                         abs_level=sect.abs_level,
                                         left=0,
                                         top=0,
                                         page=0)
                        for sect in get_document_sections_with_titles(text, sentence_list=sentence_spans)]
            set_section_coordinates(sections)

        try:
            title = next(get_titles(text))
        except StopIteration:
            title = None

        text_struct = PlainTextStructure(
            title=title,
            language=language or lang.predict_lang(text),
            pages=pages,
            sentences=sentences,
            paragraphs=paragraphs,
            sections=sections,
            table_of_contents=table_of_contents)

        char_bboxes = pdfbox_res['charBBoxes']
        pdf_coordinates = PDFCoordinates(char_bboxes=char_bboxes)
        yield text, TextAndPDFCoordinates(text_structure=text_struct,
                                          pdf_coordinates=pdf_coordinates), out_pdf_fn, page_rotate_angles
        return

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def set_section_coordinates(sections: List[PlainTextSection],
                            char_bboxes: List[List[float]],
                            pages: List[PlainTextPage]):
    # calculates left / top coordinates and the page number
    # for each section found by ML in plain text
    page_bounds = [(p.start, p.end) for p in pages]
    for sect in sections:
        char_index = sect.start if sect.start < len(char_bboxes) else len(char_bboxes) - 1
        sect.left = char_bboxes[char_index][0]
        sect.top = char_bboxes[char_index][1]
        sect.page = find_page_by_smb_index(page_bounds, sect.start) or 0


def get_sections_from_table_of_contents(
        toc_items: List[PlainTableOfContentsRecord],
        char_bboxes: List[List[float]],
        pages: List[PlainTextPage]) -> List[PlainTextSection]:
    """
    """
    sects: List[PlainTextSection] = []
    for ti in toc_items:
        sect = PlainTextSection(start=0,
                                end=0,
                                title=ti.title,
                                title_start=0,
                                title_end=0,
                                level=ti.level,
                                abs_level=ti.level,
                                left=ti.left,
                                top=ti.top,
                                page=ti.page)
        # find coordinates (start / end) by left and top
        page = pages[ti.page]
        top = ti.top  # NB: we don't invert Y-coordinate here
        start = CoordTextMap.find_closest_symbol_pos(char_bboxes, ti.left, top, page.start, page.end)
        sect.start = start
        sect.end = start + 1
        sects.append(sect)

    # make the beginning of the next section the ending of the current one
    for i, sect in enumerate(sects):
        last_page = pages[-1]
        sect.end = last_page.end
        # find the next section on the same level
        # or assume the section ends with the last document symbol
        for j in range(i + 1, len(sects)):
            if sects[j].level > sect.level:
                continue
            sect.end = sects[j].start
            break

        sect.title_start = sect.start
        sect.title_end = sect.title_start + len(sect.title)
        # TODO: detect title start - title end
    return sects


def extract_text_pdfminer(pdf_fn: str) -> str:
    output_string = StringIO()
    with open(pdf_fn, 'rb') as in_file:
        parser = PDFParser(in_file)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        device = TextConverter(rsrcmgr, output_string)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.create_pages(doc):
            interpreter.process_page(page)
    return output_string.getvalue()


def get_first_page_layout(pdf_opened_file,
                          use_advanced_detection: bool = True) -> LTPage:
    parser = PDFParser(pdf_opened_file)
    doc = PDFDocument(parser)
    rsrcmgr = PDFResourceManager()
    laparams = LAParams(all_texts=True) if use_advanced_detection else LAParams(all_texts=True, boxes_flow=None)
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    for page in PDFPage.create_pages(doc):
        interpreter.process_page(page)
        return device.get_result()

    raise Exception('Unable to build LTPage from opened file')


@dataclass
class PDFPageProcessingResults:
    page_requires_ocr: bool
    ocred_page_fn: Optional[str] = None
    ocred_page_rotation_angle: Optional[float] = None


@contextmanager
def process_pdf_page(pdf_fn: str,
                     page_num: int,
                     ocr_enabled: bool = True,
                     ocr_language: str = None,
                     ocr_timeout_sec: int = 60,
                     pdf_password: str = None) -> Generator[PDFPageProcessingResults, None, None]:
    with open(pdf_fn, 'rb') as in_file:
        if ocr_enabled:
            # Try extracting "no-text" image of the pdf page.
            # It removes all elements from the page except images having no overlapping
            # with any text element.
            # This is used to avoid the text duplication by OCR.
            with extract_page_ocr_images(pdf_fn,
                                         start_page=1,
                                         end_page=1,
                                         pdf_password=pdf_password,
                                         dpi=DPI,
                                         reset_page_rotation=False) \
                    as image_fns:
                page_image_without_text_fn = image_fns.get(1) if image_fns else None
                if page_image_without_text_fn:
                    # this returns a text-based PDF with glyph-less text only
                    # to be used for merging in front of the original PDF page layout
                    with ocr_page_to_pdf(page_image_fn=page_image_without_text_fn,
                                         language=ocr_language,
                                         timeout=ocr_timeout_sec,
                                         glyphless_text_only=True,
                                         tesseract_page_orientation_detection=True) as ocred_text_layer_pdf_fn:
                        # we return only the transparent text layer PDF and not the merged page
                        # because in the final step we will need to merge these transparent layer in front
                        # of the pages in the original PDF file to keep its small size and structure/bookmarks.
                        yield PDFPageProcessingResults(page_requires_ocr=True,
                                                       ocred_page_fn=ocred_text_layer_pdf_fn)
                        return
        # if we don't need OCR then
        yield PDFPageProcessingResults(page_requires_ocr=False)
