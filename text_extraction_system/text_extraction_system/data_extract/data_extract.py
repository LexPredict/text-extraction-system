import gc
import os
import shutil
import subprocess
from contextlib import contextmanager

import cv2
from PIL import Image
from dataclasses import dataclass
from io import StringIO
from logging import getLogger
from subprocess import CompletedProcess, PIPE
from tempfile import mkdtemp
from typing import Tuple, Generator, Optional, Dict, Any, List

import msgpack
from lexnlp.nlp.en.segments.paragraphs import get_paragraph_spans
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
from text_extraction_system.constants import TESSERACT_DEFAULT_LANGUAGE
from text_extraction_system.data_extract.lang import get_lang_detector
from text_extraction_system.ocr.ocr import ocr_page_to_pdf, get_page_orientation, OCRException
from text_extraction_system.ocr.rotation_detection import determine_rotation, \
    RotationDetectionMethod, PageRotationStatus
from text_extraction_system.pdf.pdf import extract_page_ocr_images, \
    raise_from_pdfbox_error_messages, rotate_pdf_pages
from text_extraction_system.processes import raise_from_process
from text_extraction_system.utils import LanguageConverter
from text_extraction_system_api.dto import PlainTextParagraph, PlainTextSection, PlainTextPage, \
    PlainTextStructure, PlainTextSentence, TextAndPDFCoordinates, PDFCoordinates, \
    PlainTableOfContentsRecord
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
                               render_coords_debug: bool = False,
                               read_sections_from_toc: bool = True) \
        -> Tuple[
            str, TextAndPDFCoordinates, str, Dict[int, float]]:  # text, structure, corrected_pdf_fn, page_rotate_angles
    # pdf_fn file already contains text, no OCR is required at this step

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
        try:
            log.info('Page rotation data:')
            log.info(completed_process.stdout)
        except Exception as e:
            log.error(f"Can't get page rotation data: {e}")
        raise_from_process(log, completed_process, process_title=lambda: f'Extract text and structure from {pdf_fn}')

        raise_from_pdfbox_error_messages(completed_process)

        with open(out_fn, 'rb') as pages_f:
            try:
                gc.disable()
                # see object structure in com.lexpredict.textextraction.dto.PDFPlainText
                pdfbox_res: Dict[str, Any] = msgpack.unpack(pages_f, raw=False)
            finally:
                gc.enable()

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

        # we store the rotation angles for each of the pages
        page_rotate_angles: List[float] = [pdfpage['deskewAngle'] for pdfpage in pdfbox_res['pages']]

        pages = []
        num: int = 0
        for i, p in enumerate(pdfbox_res['pages']):
            rotation = int(round(page_rotate_angles[i]))
            p_res = PlainTextPage(number=num, start=p['location'][0], end=p['location'][1],
                                  bbox=p['bbox'], rotation=rotation)
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
                      for start, end, segment, in get_paragraph_spans(text)]

        if read_sections_from_toc and table_of_contents:
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
            set_section_coordinates(sections, pdfbox_res['charBBoxes'], pages)

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
    sects.sort(key=lambda s: s.start)

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
    # TODO: this method is for testing purposes only
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
    # TODO: this method is for testing purposes only
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
    rotation_angle: Optional[float] = None


@contextmanager
def process_pdf_page(pdf_fn: str,
                     page_image_without_text_fn: str,
                     ocr_enabled: bool = True,
                     ocr_language: str = None,
                     ocr_timeout_sec: int = 60,
                     detect_orientation_tesseract=False) -> PDFPageProcessingResults:
    if not ocr_enabled:
        yield PDFPageProcessingResults(page_requires_ocr=False)
        return

    rot_angle = 0
    orientation = None
    if detect_orientation_tesseract:
        try:
            orientation = get_page_orientation(page_image_without_text_fn,
                                               language=ocr_language or TESSERACT_DEFAULT_LANGUAGE)
        except Exception as e:
            error_text = OCRException.TOO_FEW_CHARACTERS_ERROR if OCRException.TOO_FEW_CHARACTERS_ERROR in str(e) else e
            log.error(f'Cant get page orientation by Tesseract: {error_text}')

        # TODO: presently orientation "probability" threshold is taken arbitrary
        ORIENTATION_THRESHOLD = 3
        if orientation and orientation[0] and orientation[1] > ORIENTATION_THRESHOLD:
            # rotate the document
            # rotate_pdf_pages(pdf_fn, pdf_fn, orientation[0])
            # rotate the image
            rotate_image(orientation[0], page_image_without_text_fn, page_image_without_text_fn)

    # the image might be rotated. Then we try to determine the image rotation angle
    # based on opencv algorithms and rotate the image back.
    # Even if the image is still rotated, OCR will extract the text. That's fine
    # if the image rotation angle is a multiple of 90 degree.
    rot_status = determine_rotation(page_image_without_text_fn, RotationDetectionMethod.DILATED_ROWS)

    if should_correct_rotation(pdf_fn, rot_status):
        # we don't rotate images by more than 45 degree angle
        rot_angle = normalize_angle_90(rot_status.angle)

        # rotate the document
        rotate_pdf_pages(pdf_fn, pdf_fn, rot_angle)

        # rotate extracted image
        rotate_image(rot_angle, page_image_without_text_fn, page_image_without_text_fn)

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
                                       ocred_page_fn=ocred_text_layer_pdf_fn,
                                       rotation_angle=rot_angle)


def normalize_angle_90(rot_angle: float) -> float:
    # inscribe the angle in -45 ... 45 degrees
    rot_sign = -1 if rot_angle < 0 else 1
    rot_angle = abs(rot_angle)
    if rot_angle > 45:
        rot_angle = rot_angle - 90
        rot_angle = rot_sign * rot_angle
    else:
        rot_angle = rot_sign * rot_angle
    return rot_angle


def rotate_page_back(page_image_without_text_fn: str, rot_angle: float):
    # NB: we use PIL because it's faster: PIL - load, rotate and save take 0.064s
    # cv2 - load, rotate and save take 0.236s
    img = Image.open(page_image_without_text_fn)
    img = img.convert('RGB')
    img = img.rotate(rot_angle, fillcolor=(255, 255, 255), expand=True)
    img.save(page_image_without_text_fn)


def should_correct_rotation(pdf_fn: str, rot_status: PageRotationStatus) -> bool:
    """
    The page may contain much text and just a small image, that our CV2 based logic
    may detect as rotated. And then we rotate the page itself.
    This functions prevents rotating the page if:
    - either the page contains enough text
    - or the image occupies a tiny part of the page.
    """
    if rot_status.angle == 0:
        return False
    if rot_status.occupied_area_percent is None:
        return True

    java_modules_path = get_settings().java_modules_path
    args = ['java', '-cp', f'{java_modules_path}/*',
            'com.lexpredict.textextraction.PDFSymbolsCalculator',
            '--original-pdf', pdf_fn]

    # compare area, occupied by image parts (that might be text) and the rest of the page
    try:
        p = subprocess.Popen(args, stderr=PIPE, stdout=PIPE)
        (out, err) = p.communicate()
        symbol_count = int(out.decode("utf-8"))
    except Exception as e:
        log.error(f'Error in should_correct_rotation({pdf_fn}) while calling PDFSymbolsCalculator: {e}')
        symbol_count = 0

    word_percent = 100 * symbol_count / 2700  # 2700 is an estimation for avg words per page
    if word_percent > 40:
        return False
    if word_percent > 10 and rot_status.occupied_area_percent < 10:
        return False
    return word_percent < 3


def rotate_image(angle: float, src_path: str, dst_path: str) -> None:
    src = cv2.imread(src_path)
    h, w, _ = src.shape
    rotate_matrix = cv2.getRotationMatrix2D(center=(w/2, h/2), angle=angle, scale=1)

    def should_swap_hw(a):
        a = abs(a)
        a = abs(a - 180 * round(a / 180))
        return abs(round(a / 90)) > 0

    if should_swap_hw(angle):
        h, w = w, h

    rotated_image = cv2.warpAffine(src=src, M=rotate_matrix, dsize=(w, h), borderValue=(255, 255, 255))
    cv2.imwrite(dst_path, rotated_image)
