import os
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from logging import getLogger
from subprocess import CompletedProcess, PIPE
from tempfile import mkdtemp
from typing import List, Tuple, Generator, Optional, Dict, Any

import msgpack
from camelot.core import Table as CamelotTable
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

from text_extraction_system.config import get_settings
from text_extraction_system.data_extract.camelot.camelot import extract_tables
from text_extraction_system.data_extract.lang import get_lang_detector
from text_extraction_system.ocr.ocr import ocr_page_to_pdf, deskew
from text_extraction_system.pdf.pdf import page_requires_ocr, extract_page_ocr_images, \
    raise_from_pdfbox_error_messages, merge_pdf_pages
from text_extraction_system.processes import raise_from_process
from text_extraction_system.utils import LanguageConverter
from text_extraction_system_api.dto import PlainTextParagraph, PlainTextSection, PlainTextPage, PlainTextStructure, \
    PlainTextSentence, TextAndPDFCoordinates, PDFCoordinates

log = getLogger(__name__)
PAGE_SEPARATOR = '\n\n\f'
DPI: int = 300


def extract_text_and_structure(pdf_fn: str,
                               pdf_password: str = None,
                               timeout_sec: int = 3600,
                               glyph_enhancing: bool = False,
                               remove_non_printable: bool = False,
                               language: str = "") \
        -> Tuple[str, TextAndPDFCoordinates]:
    java_modules_path = get_settings().java_modules_path

    # Convert language to language code
    lang_converter = LanguageConverter()
    language, locale_code = lang_converter.get_language_and_locale_code(language)

    temp_dir = mkdtemp(prefix='pdf_text_')
    out_fn = os.path.join(temp_dir, os.path.splitext(os.path.basename(pdf_fn))[0] + '.msgpack')
    try:
        args = ['java', '-cp', f'{java_modules_path}/*',
                'com.lexpredict.textextraction.GetTextFromPDF',
                pdf_fn,
                out_fn,
                '-f', 'pages_msgpack']

        if pdf_password:
            args.append('-p')
            args.append(pdf_password)

        if glyph_enhancing:
            args.append('-ge')
            args.append('true')

        if remove_non_printable:
            args.append('-rn')
            args.append('true')

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
            pdf_coordinates = PDFCoordinates(char_bboxes_with_page_nums=pdfbox_res['charBBoxesWithPageNums'])
            text_struct = PlainTextStructure(title='',
                                             language=language or 'en',  # FastText returns English for empty strings
                                             pages=[],
                                             sentences=[],
                                             paragraphs=[],
                                             sections=[])
            return text, TextAndPDFCoordinates(text_structure=text_struct, pdf_coordinates=pdf_coordinates)

        pages = []
        num: int = 0
        for p in pdfbox_res['pages']:
            p_res = PlainTextPage(number=num, start=p['location'][0], end=p['location'][1], bbox=p['bbox'])
            pages.append(p_res)
            num += 1

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

        sections = [PlainTextSection(title=sect.title,
                                     start=sect.start,
                                     end=sect.end,
                                     title_start=sect.title_start,
                                     title_end=sect.title_end,
                                     level=sect.level,
                                     abs_level=sect.abs_level)
                    for sect in get_document_sections_with_titles(text, sentence_list=sentence_spans)]

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
            sections=sections)

        char_bboxes_with_page_nums = pdfbox_res['charBBoxesWithPageNums']
        pdf_coordinates = PDFCoordinates(char_bboxes_with_page_nums=char_bboxes_with_page_nums)
        return text, TextAndPDFCoordinates(text_structure=text_struct,
                                           pdf_coordinates=pdf_coordinates)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


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


def get_first_page_layout(pdf_opened_file) -> LTPage:
    parser = PDFParser(pdf_opened_file)
    doc = PDFDocument(parser)
    rsrcmgr = PDFResourceManager()
    laparams = LAParams(all_texts=True)
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
    camelot_tables: Optional[List[CamelotTable]] = None


@contextmanager
def process_pdf_page(pdf_fn: str,
                     page_num: int,
                     ocr_enabled: bool = True,
                     ocr_language: str = None,
                     ocr_timeout_sec: int = 60,
                     pdf_password: str = None) -> Generator[PDFPageProcessingResults, None, None]:
    # generate a pair of image representations of the PDF page:
    # 1. image of the original page as is - to be used in Camelot for the optical detection of the table borders;
    # 2. image of the layout of the original page with only image/picture elements left on it and
    # all the text elements removed - to be used for OCR by Tesseract to avoid the text duplication.
    #
    # We extract both images in one step to decrease the number of times we parse the PDF.
    with extract_page_ocr_images(pdf_fn, start_page=1, end_page=1, pdf_password=pdf_password, dpi=DPI) as image_fns:
        assert image_fns and image_fns[0] and image_fns[0][0] and image_fns[0][1], \
            "A page requires OCR but no images have been extracted."

        page_image_with_text_fn, page_image_without_text = image_fns[0]
        with open(pdf_fn, 'rb') as in_file:
            # build pdfminer page layout - used for detecting if the page requires OCR or not
            original_page_layout = get_first_page_layout(in_file)

            if ocr_enabled and page_requires_ocr(original_page_layout):
                # this detects scanned text rotation angle
                # and returns either the original image fn (if detected angle is almost zero or > 45)
                # or the fn of the image rotated for the text to be horizontal
                with deskew(image_fn=page_image_without_text, deskewed_image_dpi=DPI) \
                        as (did_deskew, angle, prepared_image_fn):
                    # this returns a text-based PDF with glyph-less text only
                    # to be used for merging in front of the original PDF page layout
                    with ocr_page_to_pdf(page_image_fn=prepared_image_fn,
                                         language=ocr_language,
                                         timeout=ocr_timeout_sec,
                                         glyphless_text_only=True) as ocred_text_layer_pdf_fn:
                        # We need fully merged PDF page here for the proper work of the table extraction by Camelot
                        with merge_pdf_pages(original_pdf_fn=pdf_fn,
                                             original_pdf_password=pdf_password,
                                             single_page_merge_num_file_rotate=(1,
                                                                                ocred_text_layer_pdf_fn,
                                                                                angle if did_deskew else None)) \
                                as ocred_pdf_for_tables:
                            with open(ocred_pdf_for_tables, 'rb') as ocred_in_file:
                                ocred_page_layout = get_first_page_layout(ocred_in_file)
                                camelot_tables = extract_tables(page_num, ocred_page_layout, page_image_with_text_fn)

                        # But we return only the transparent text layer PDF and not the merged page
                        # because in the final step we will need to merge these transparent layer in front
                        # of the pages in the original PDF file to keep its small size and structure/bookmarks.
                        yield PDFPageProcessingResults(page_requires_ocr=True,
                                                       ocred_page_fn=ocred_text_layer_pdf_fn,
                                                       ocred_page_rotation_angle=angle if did_deskew else None,
                                                       camelot_tables=camelot_tables)
            else:
                # if we don't need OCR then execute Camelot on the original PDF page
                camelot_tables = extract_tables(page_num, original_page_layout, page_image_with_text_fn)
                yield PDFPageProcessingResults(page_requires_ocr=False,
                                               camelot_tables=camelot_tables)
