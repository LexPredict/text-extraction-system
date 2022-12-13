import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from logging import getLogger
from subprocess import CompletedProcess, PIPE
from tempfile import mkdtemp
from typing import Generator, List, Optional, Tuple, Dict

import pikepdf
from pdf2image import convert_from_path
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTImage, LTItem, LTLayoutContainer, LTPage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

from text_extraction_system.config import get_settings
from text_extraction_system.constants import DPI
from text_extraction_system.pdf.utils import pikepdf_opened_w_error
from text_extraction_system.processes import raise_from_process, render_process_msg
from text_extraction_system.utils import page_num_to_fn

log = getLogger(__name__)


def page_requires_ocr(page_layout: LTPage) -> bool:
    text_cover, image_cover = calc_covers(page_layout)
    return text_cover < 0.3 * image_cover


def iterate_pages(pdf_fn: str, use_advanced_detection: bool = False) -> Generator[LTPage, None, None]:
    with open(pdf_fn, 'rb') as pdf_f:
        parser = PDFParser(pdf_f)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        laparams = LAParams(all_texts=True, grid_size=0) if use_advanced_detection \
            else LAParams(all_texts=True, boxes_flow=None, grid_size=0)
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for n, page in enumerate(PDFPage.create_pages(doc)):
            try:
                interpreter.process_page(page)
            except TypeError as e:
                # faced to Exception in pdfminer.pdfinterpr.fo_TD when it tries to multipl. float, int and bytes
                # original exception: "can't multiply sequence by non-int of type 'float'"
                log.warning(f'Failed to correctly process page layout for page #{n}, '
                            f'original exception: "{e.__repr__()}"; skip it.')
            page_layout: LTPage = device.get_result()
            yield page_layout


PAGE_NUM_RE = re.compile(r'\d+$')
PDF_BOX_CRASH = {
    re.compile(r'SEVERE:\s+Cannot\sread.{1,100}image')
}


def raise_from_pdfbox_error_messages(completed_process: CompletedProcess):
    for r in PDF_BOX_CRASH:
        if r.search(completed_process.stderr) or r.search(completed_process.stdout):
            raise Exception(f'PDFBox process output contains error messages\n{render_process_msg(completed_process)}')


@contextmanager
def extract_page_images(pdf_fn: str,
                        start_page: int = None,
                        end_page: int = None,
                        pdf_password: str = None,
                        timeout_sec: int = 1800,
                        dpi: int = DPI) -> Generator[List[str], None, None]:
    java_modules_path = get_settings().java_modules_path
    temp_dir = mkdtemp(prefix='pdf_images_')
    basefn = os.path.splitext(os.path.basename(pdf_fn))[0]
    try:
        args = ['java', '-cp', f'{java_modules_path}/*', 'org.apache.pdfbox.tools.PDFToImage',
                '-format', 'png',
                '-dpi', f'{dpi}',
                '-quality', '1',
                '-prefix', f'{temp_dir}/{basefn}__']
        if pdf_password:
            args += ['-password', pdf_password]
        if start_page is not None:
            args += ['-startPage', str(start_page)]
        if end_page is not None:
            args += ['-endPage', str(end_page)]
        args += [pdf_fn]
        completed_process: CompletedProcess = subprocess.run(args, check=False, timeout=timeout_sec,
                                                             universal_newlines=True, stderr=PIPE, stdout=PIPE)
        raise_from_process(log, completed_process, process_title=lambda: f'Extract page images from {pdf_fn}')
        raise_from_pdfbox_error_messages(completed_process)

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


@contextmanager
def extract_page_ocr_images(pdf_fn: str,
                            start_page: int = None,
                            end_page: int = None,
                            pdf_password: str = None,
                            timeout_sec: int = 1800,
                            reset_page_rotation: bool = False,
                            dpi: int = DPI) -> Generator[Dict[int, str], None, None]:
    java_modules_path = get_settings().java_modules_path
    temp_dir_no_text = mkdtemp(prefix='pdf_images_')
    base_fn = os.path.splitext(os.path.basename(pdf_fn))[0]
    try:
        args = ['java', '-cp', f'{java_modules_path}/*', 'com.lexpredict.textextraction.getocrimages.GetOCRImages',
                pdf_fn,
                '--format', 'png',
                '--dpi', f'{dpi}',
                '--output-prefix-no-text', f'{temp_dir_no_text}/{base_fn}__']
        if pdf_password:
            args += ['--password', pdf_password]
        if start_page is not None:
            args += ['--start-page', str(start_page)]
        if end_page is not None:
            args += ['--end-page', str(end_page)]
        if reset_page_rotation:
            args += ['--reset-page-rotation']
        completed_process: CompletedProcess = subprocess.run(args, check=False, timeout=timeout_sec,
                                                             universal_newlines=True, stderr=PIPE, stdout=PIPE)
        raise_from_process(log, completed_process,
                           process_title=lambda: f'Extract page images for OCR needs (with text removed) from {pdf_fn}')
        raise_from_pdfbox_error_messages(completed_process)

        # Output of GetOCRImages is a set of files with the names generated as:
        # {prefix}+{page_num_1_based}.{ext}
        # We used "{temp_dir}/{basefn}__" as the prefix.
        # Now we need to get the page numbers from the filenames and return the list of file names
        # ordered by page number.
        # For the "no-text" images: for the pages having no images which are not overlapped with
        # any text element it stores no page image.
        page_by_num_no_text: Dict[int, str] = dict()
        for fn in os.listdir(temp_dir_no_text):
            page_num = PAGE_NUM_RE.search(os.path.splitext(fn)[0]).group(0)
            page_no_text_fn = os.path.join(temp_dir_no_text, fn)
            page_by_num_no_text[int(page_num)] = page_no_text_fn
        yield page_by_num_no_text
    finally:
        shutil.rmtree(temp_dir_no_text, ignore_errors=True)


def get_pdf_pages_amount(pdf_fn: str):
    return len(pikepdf.Pdf.open(pdf_fn).pages)


@contextmanager
def extract_page_images_from_pdf(pdf_fn: str, should_clean_text: bool = True, start_page: int = 0, end_page: int = 0,
                                 pdf_password: str = None, dpi: int = DPI) -> Generator[Dict[int, str], None, None]:
    temp_dir_images = mkdtemp(prefix='pdf_images_')
    base_fn = os.path.splitext(os.path.basename(pdf_fn))[0]
    page_by_num_image: Dict[int, str] = dict()
    doc = pikepdf.Pdf.open(pdf_fn) if not pdf_password else pikepdf.Pdf.open(pdf_fn, password=pdf_password)
    for i in range(start_page, abs(end_page) or len(doc.pages)):
        if not doc.pages[i].images.keys():
            continue
        if should_clean_text:
            # Clean content stream
            cst = pikepdf.parse_content_stream(doc.pages[i])
            to_remove = [i for i, (_, op) in enumerate(cst) if op in (pikepdf.Operator("BT"), pikepdf.Operator("ET"))]
            to_remove = [to_remove[i:i + 2] for i in range(0, len(to_remove), 2)][::-1]
            for start, end in to_remove:
                del cst[start:end]
            new_content_stream = pikepdf.unparse_content_stream(cst)
            doc.pages[i].Contents = doc.make_stream(new_content_stream)
        # Create separate pdf-page
        dst = pikepdf.Pdf.new()
        dst.pages.append(doc.pages[i])
        page_image_fn = os.path.join(temp_dir_images, f'{base_fn}__{page_num_to_fn(i)}.pdf')
        dst.save(page_image_fn)
        # Convert pdf to image
        pdf_pages = convert_from_path(page_image_fn, dpi)
        page_image_fn = f"{page_image_fn[:-3]}png"
        pdf_pages[0].save(page_image_fn, 'PNG')
        page_by_num_image[i] = page_image_fn
    yield page_by_num_image
    shutil.rmtree(temp_dir_images, ignore_errors=True)


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
    append_name = f'_{(page_end + 1):04}' if page_start != page_end else ''
    fn = f'{os.path.splitext(fn)[0]}_{(page_start + 1):04}{append_name}.pdf'
    return fn


@contextmanager
def split_pdf_to_page_blocks(src_pdf_fn: str,
                             pages_per_block: int = 1,
                             page_block_base_name: str = None) -> Generator[List[str], None, None]:
    with pikepdf_opened_w_error(src_pdf_fn) as pdf:
        if len(pdf.pages) < 1:
            yield []
            return
        if len(pdf.pages) < pages_per_block:
            yield [src_pdf_fn]
            return
        page_block_base_name = page_block_base_name or os.path.basename(src_pdf_fn)
        temp_dir = mkdtemp()
        try:
            res: List[str] = list()
            page_start: int = 0
            out_pdf: Optional[pikepdf.Pdf] = None
            for n, page in enumerate(pdf.pages):
                if n % pages_per_block == 0:
                    if out_pdf is not None:
                        out_fn = build_block_fn(str(page_block_base_name), page_start, n - 1)
                        out_pdf.save(os.path.join(temp_dir, out_fn))
                        out_pdf.close()
                        res.append(os.path.join(temp_dir, out_fn))
                    page_start = n
                    out_pdf = pikepdf.new()
                out_pdf.pages.append(page)
            if out_pdf is not None and len(out_pdf.pages) > 0:
                out_fn = build_block_fn(str(page_block_base_name), page_start, n)
                out_pdf.save(os.path.join(temp_dir, out_fn))
                out_pdf.close()
                res.append(os.path.join(temp_dir, out_fn))
            yield res
        finally:
            shutil.rmtree(temp_dir)


@contextmanager
def get_page_from_pdf(pdf_fn: str, page_number: int = 0) -> Generator[str, None, None]:
    pdf_page_fn = f'{pdf_fn[:-4]}__{page_num_to_fn(page_number)}.pdf'
    dst = pikepdf.Pdf.new()
    try:
        with pikepdf.Pdf.open(pdf_fn) as doc:
            dst.pages.append(doc.pages[page_number])
            dst.save(pdf_page_fn)
        yield pdf_page_fn
    except IndexError:
        ...
    finally:
        if os.path.isfile(pdf_page_fn):
            os.remove(pdf_page_fn)


@contextmanager
def merge_pdf_pages(original_pdf_fn: str,
                    page_pdf_dir: str = None,
                    single_page_merge_num_file_rotate: Tuple[int, str, Optional[float]] = None,
                    original_pdf_password: str = None,
                    timeout_sec: int = 3000) -> Generator[str, None, None]:
    temp_dir = mkdtemp()
    try:
        dst_pdf_fn = os.path.join(temp_dir, os.path.basename(original_pdf_fn))
        java_modules_path = get_settings().java_modules_path
        args = ['java', '-cp', f'{java_modules_path}/*', 'com.lexpredict.textextraction.mergepdf.MergeInPageLayers',
                '--original-pdf', original_pdf_fn,
                '--dst-pdf', dst_pdf_fn]
        if page_pdf_dir:
            args += ['--page-dir', page_pdf_dir]
        if single_page_merge_num_file_rotate:
            merge_page_num, merge_page_fn, merge_page_rotate = single_page_merge_num_file_rotate
            args += [f'{merge_page_num}={merge_page_fn}']
            if merge_page_rotate:
                args += [f'rotate_{merge_page_num}={merge_page_rotate}']
        if original_pdf_password:
            args += ['--password', original_pdf_password]
        completed_process: CompletedProcess = subprocess.run(args, check=False, timeout=timeout_sec,
                                                             universal_newlines=True, stderr=PIPE, stdout=PIPE)
        raise_from_process(log, completed_process, process_title=lambda: f'Extract page images for OCR needs '
                                                                         f'(with text removed) from {original_pdf_fn}')
        raise_from_pdfbox_error_messages(completed_process)
        yield dst_pdf_fn
    finally:
        shutil.rmtree(temp_dir)


@contextmanager
def rotate_pdf_pages(original_pdf_fn: str,
                     resulted_pdf_fn: str,
                     rotation_angle: float,
                     timeout_sec: int = 3000):
    java_modules_path = get_settings().java_modules_path
    args = ['java', '-cp', f'{java_modules_path}/*', 'com.lexpredict.textextraction.RotatePdf',
            '--original-pdf', original_pdf_fn,
            '--dst-pdf', resulted_pdf_fn,
            '--rot-angle', str(rotation_angle)]
    completed_process: CompletedProcess = subprocess.run(args, check=False, timeout=timeout_sec,
                                                         universal_newlines=True, stderr=PIPE, stdout=PIPE)
    raise_from_process(log, completed_process, process_title=lambda: f'Rotate PDF pages for {original_pdf_fn}')
    raise_from_pdfbox_error_messages(completed_process)
