import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from logging import getLogger
from subprocess import CompletedProcess
from subprocess import PIPE
from tempfile import mkdtemp
from typing import Generator
from typing import List, Optional, Tuple, Dict

import pikepdf
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTImage, LTItem, LTLayoutContainer, LTPage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

from text_extraction_system.config import get_settings
from text_extraction_system.processes import raise_from_process

log = getLogger(__name__)


def page_requires_ocr(page_layout: LTPage) -> bool:
    text_cover, image_cover = calc_covers(page_layout)
    return text_cover < 0.3 * image_cover


def iterate_pages(pdf_fn: str) -> Generator[LTPage, None, None]:
    with open(pdf_fn, 'rb') as pdf_f:
        parser = PDFParser(pdf_f)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.create_pages(doc):
            interpreter.process_page(page)
            page_layout: LTPage = device.get_result()
            yield page_layout


PAGE_NUM_RE = re.compile(r'\d+$')


@contextmanager
def extract_page_images(pdf_fn: str,
                        start_page: int = None,
                        end_page: int = None,
                        pdf_password: str = None) -> Generator[List[str], None, None]:
    java_modules_path = get_settings().java_modules_path

    temp_dir = mkdtemp(prefix='pdf_images_')
    basefn = os.path.splitext(os.path.basename(pdf_fn))[0]
    try:
        args = ['java', '-cp', f'{java_modules_path}/*',
                'org.apache.pdfbox.tools.PDFToImage',
                '-format', 'png',
                '-dpi', '300',
                '-quality', '1',
                '-prefix', f'{temp_dir}/{basefn}__']
        if pdf_password:
            args += ['-password', pdf_password]

        if start_page is not None:
            args += ['-startPage', str(start_page)]

        if end_page is not None:
            args += ['-endPage', str(end_page)]

        args += [pdf_fn]

        completed_process: CompletedProcess = subprocess.run(args, check=False, timeout=600,
                                                             universal_newlines=True, stderr=PIPE, stdout=PIPE)
        raise_from_process(log, completed_process, process_title=lambda: f'Extract page images from {pdf_fn}')

        # Output of PDFToImage is a set of files with the names generated as:
        # {prefix}+{page_num_1_based}.{ext}
        # We used "{temp_dir}/{basefn}__" as the prefix.
        # Now we need to get the page numbers from the filenames and return the list of file names
        # ordered by page number.
        page_by_num: Dict[int, str] = dict()
        for fn in os.listdir(temp_dir):
            page_num = PAGE_NUM_RE.search(os.path.splitext(fn)[0]).group(0)
            page_by_num[int(page_num)] = os.path.join(temp_dir, fn)

        yield [page_by_num[key] for key in sorted(page_by_num.keys())]

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
