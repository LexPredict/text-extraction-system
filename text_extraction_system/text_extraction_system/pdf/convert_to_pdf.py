import logging
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from subprocess import CompletedProcess, PIPE
from typing import Generator

from PIL import Image

from text_extraction_system.config import get_settings
from text_extraction_system.pdf.errors import InputFileDoesNotExist, OutputPDFDoesNotExistAfterConversion
from text_extraction_system.pdf.utils import separate_filename_basename_and_extension, run_process
from text_extraction_system.processes import raise_from_process, render_process_msg

log = logging.getLogger(__name__)


def convert_image_to_pdf(src_fn: str, out_fn: str, timeout_sec: int = 1800) -> CompletedProcess:
    """
    Converts image to pdf file using custom Java solution
    """
    args = ['java', '-cp', f'{get_settings().java_modules_path}/*', 'com.lexpredict.textextraction.MakePDFFromImages',
            out_fn, src_fn]
    return run_process(args, timeout_sec)


@contextmanager
def convert_to_pdf(src_fn: str, timeout_sec: int = 1800) -> Generator[str, None, None]:
    """
    Converts the specified file to pdf file.
    Soffice converter allows specifying the output directory. The output file name is generated
    by changing the extension to ".pdf". To avoid file name conflicts and additional operations
    the output file is written into a temporary directory and next yielded to the caller.
    After returning from the yield the output file and the output temp directory are removed.
    """
    if not os.path.isfile(src_fn) and not os.path.isfile(src_fn):
        raise InputFileDoesNotExist(src_fn)
    temp_dir = tempfile.mkdtemp()
    source_fn = src_fn
    src_fn, src_fn_base, src_ext = separate_filename_basename_and_extension(src_fn, temp_dir)
    out_fn = os.path.join(temp_dir, src_fn_base + '.pdf')

    # Bypass pdf file
    if src_ext == 'pdf':
        return src_fn
    try:
        if src_ext.lower() in {'.tiff', '.jpg', '.jpeg', '.png'}:
            if src_ext.lower() == '.png':
                im = Image.open(source_fn)
                rgb_im = im.convert('RGB')
                rgb_im.save(source_fn)
            completed_process = convert_image_to_pdf(src_fn, out_fn, timeout_sec)
        else:
            java_modules_path = get_settings().java_modules_path
            args = ['java', '-cp', f'{java_modules_path}/*', 'com.lexpredict.textextraction.ConvertToPDF',
                    '--original-doc', src_fn,
                    '--dst-pdf', out_fn]
            completed_process: CompletedProcess = subprocess.run(args, check=False, timeout=timeout_sec,
                                                                 universal_newlines=True, stderr=PIPE, stdout=PIPE)
        raise_from_process(log, completed_process, lambda: f'Converting {src_fn} to pdf.')
        if not os.path.isfile(out_fn):
            raise OutputPDFDoesNotExistAfterConversion(f'Unable to convert {src_fn} to pdf. Output file does not exist '
                                                       f'after conversion.\n' + render_process_msg(completed_process))
        yield out_fn
    finally:
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)
