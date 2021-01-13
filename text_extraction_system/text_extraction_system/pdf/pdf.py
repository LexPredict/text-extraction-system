import os
import shutil
from contextlib import contextmanager
from logging import getLogger
from tempfile import mkdtemp
from typing import List, Optional, Tuple, Generator, Dict

import pdf2image
import pikepdf
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTImage, LTItem, LTLayoutContainer, LTPage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

log = getLogger(__name__)

def page_requires_ocr(page_layout: LTPage) -> bool:
    text_cover, image_cover = calc_covers(page_layout)
    return text_cover < 0.3 * image_cover

def find_pages_requiring_ocr(pdf_fn: str) -> Optional[List[int]]:
    pages = list()
    with open(pdf_fn, 'rb') as f:
        parser = PDFParser(f)
        document = PDFDocument(parser)
        if not document.is_extractable:
            return None
        rsrcmgr = PDFResourceManager()

        laparams = LAParams()

        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        page_num = 0
        for page in PDFPage.create_pages(document):
            interpreter.process_page(page)
            layout: LTPage = device.get_result()
            if page_requires_ocr(layout):
                pages.append(page_num)
            page_num += 1

    return pages


def get_page_sequences(pages: Optional[List[int]]) -> Optional[List[List[int]]]:
    pages = sorted(set(pages))
    if not pages:
        return None
    res = list()
    cur_sequence = None
    for page in pages:
        if cur_sequence is None:
            cur_sequence = [page, page]
        elif page != cur_sequence[1] + 1:
            res.append(cur_sequence)
            cur_sequence = [page, page]
        else:  # page = prev + 1
            cur_sequence[1] = page

    if cur_sequence is not None:
        res.append(cur_sequence)
    return res


def extract_page_images(pdf_fn: str, pages: List[int]) -> Generator[Tuple[int, str], None, None]:
    temp_dir = mkdtemp(prefix='pdf2image_')

    try:
        for page_seq in get_page_sequences(pages):
            first_page = page_seq[0]
            last_page = page_seq[1]
            seq_dir = os.path.join(temp_dir, f'{first_page}_{last_page}')
            os.mkdir(seq_dir)
            image_fns = pdf2image.convert_from_path(pdf_path=pdf_fn,
                                                    dpi=300,
                                                    output_folder=seq_dir,
                                                    thread_count=4,
                                                    first_page=first_page + 1,  # pdf2image expects first page to be 1
                                                    last_page=last_page + 1,  # and not 0
                                                    paths_only=True,
                                                    fmt='png')
            page_num = first_page
            for image_fn in image_fns:
                assert page_num <= last_page
                yield page_num, image_fn
                os.remove(image_fn)
                page_num += 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@contextmanager
def extract_all_page_images(pdf_fn: str) -> Generator[List[str], None, None]:
    log.info('Rendering PDF pages to images for further using in table detection and OCR...')
    temp_dir = mkdtemp(prefix='pdf2image_')

    try:
        yield pdf2image.convert_from_path(pdf_path=pdf_fn,
                                          dpi=300,
                                          output_folder=temp_dir,
                                          thread_count=4,
                                          paths_only=True,
                                          fmt='png')
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def calc_covers(lt_obj: LTItem) -> Tuple[int, int]:
    text_cover = 0
    image_cover = 0
    if isinstance(lt_obj, (LTTextBox, LTTextLine)):
        text_cover += (lt_obj.x1 - lt_obj.x0) * (lt_obj.y1 - lt_obj.y0)
    elif isinstance(lt_obj, LTImage):
        image_cover += (lt_obj.x1 - lt_obj.x0) * (lt_obj.y1 - lt_obj.y0)
    elif isinstance(lt_obj, LTLayoutContainer):
        for item in lt_obj:
            t, i = calc_covers(item)
            text_cover += t
            image_cover += i
    return text_cover, image_cover


def build_block_fn(src_fn: str, page_start: int, page_end: int) -> str:
    fn: str = os.path.basename(src_fn)
    if page_start == page_end:
        fn = f'{os.path.splitext(fn)[0]}_{(page_start + 1):04}.pdf'
    else:
        fn = f'{os.path.splitext(fn)[0]}_{(page_start + 1):04}_{(page_end + 1):04}.pdf'
    return fn


def split_pdf_to_page_blocks(src_pdf_fn: str,
                             dst_dir: str,
                             pages_per_block: int = 1,
                             page_block_base_name: str = None, ) -> List[str]:
    if not page_block_base_name:
        page_block_base_name = os.path.basename(src_pdf_fn)
    res: List[str] = list()
    with pikepdf.open(src_pdf_fn) as pdf:
        if len(pdf.pages) < 1:
            return res

        if len(pdf.pages) < pages_per_block:
            dst_fn = os.path.join(dst_dir, page_block_base_name)
            shutil.copy(src_pdf_fn, dst_fn)
            res.append(dst_fn)
            return res

        page_start: int = 0
        out_pdf: Optional[pikepdf.Pdf] = None
        try:
            for n, page in enumerate(pdf.pages):
                if n % pages_per_block == 0:
                    if out_pdf is not None:
                        out_fn = build_block_fn(str(page_block_base_name), page_start, n - 1)
                        out_pdf.save(os.path.join(dst_dir, out_fn))
                        out_pdf.close()
                        res.append(os.path.join(dst_dir, out_fn))

                    page_start = n
                    out_pdf = pikepdf.new()

                out_pdf.pages.append(page)

            if out_pdf is not None and len(out_pdf.pages) > 0:
                out_fn = build_block_fn(str(page_block_base_name), page_start, n)
                out_pdf.save(os.path.join(dst_dir, out_fn))
                res.append(os.path.join(dst_dir, out_fn))
        finally:
            out_pdf.close()

    return res


def join_pdf_blocks(block_fns: List[str], dst_fn: str):
    if len(block_fns) == 1:
        shutil.copy(block_fns[0], dst_fn)
        return

    with pikepdf.new() as dst_pdf:  # type: pikepdf.Pdf
        for block_fn in block_fns:
            with pikepdf.open(block_fn) as block_pdf:
                dst_pdf.pages.extend(block_pdf.pages)
        dst_pdf.save(dst_fn)


@contextmanager
def merge_pfd_pages(original_pdf_fn: str, replace_page_num_to_page_pdf_fn: Dict[int, str]) \
        -> Generator[str, None, None]:
    temp_dir = mkdtemp()
    try:
        with pikepdf.open(original_pdf_fn) as pdf:  # type: pikepdf.Pdf
            dst_pdf: pikepdf.Pdf = pikepdf.new()
            for n, page in enumerate(pdf.pages):
                replace_pdf_fn: str = replace_page_num_to_page_pdf_fn.get(n)
                if not replace_pdf_fn:
                    dst_pdf.pages.append(page)
                else:
                    with pikepdf.open(replace_pdf_fn) as replace_pdf:  # type: pikepdf.Pdf
                        dst_pdf.pages.append(replace_pdf.pages[0])
            dst_pdf_fn = os.path.join(temp_dir, os.path.basename(original_pdf_fn))
            dst_pdf.save(dst_pdf_fn)
            yield dst_pdf_fn
    finally:
        shutil.rmtree(temp_dir)


@contextmanager
def cleanup_pdf(original_pdf_fn: str) -> Generator[str, None, None]:
    temp_dir = mkdtemp()
    try:
        with pikepdf.open(original_pdf_fn) as pdf:  # type: pikepdf.Pdf
            pdf.remove_unreferenced_resources()
            dst_pdf_fn = os.path.join(temp_dir, os.path.basename(original_pdf_fn))
            pdf.save(dst_pdf_fn)
            yield dst_pdf_fn
    finally:
        shutil.rmtree(temp_dir)
