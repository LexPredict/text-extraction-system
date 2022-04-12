import logging
import os
import subprocess
import tempfile
from contextlib import contextmanager
from subprocess import CompletedProcess
from subprocess import PIPE
from typing import Generator

from text_extraction_system.config import get_settings
from text_extraction_system.locking.socket_lock import get_lock
from text_extraction_system.pdf.soffice_utils import OfficeDocumentConverter
from text_extraction_system.processes import raise_from_process, render_process_msg

log = logging.getLogger(__name__)


class ConvertToPDFFailed(Exception):
    pass


class OutputPDFDoesNotExistAfterConversion(ConvertToPDFFailed):
    pass


class InputFileDoesNotExist(ConvertToPDFFailed):
    pass


def _run_process(args, timeout: int) -> CompletedProcess:
    return subprocess.run(args, check=False, timeout=timeout, universal_newlines=True, stderr=PIPE, stdout=PIPE)


@contextmanager
def convert_to_pdf(src_fn: str,
                   timeout_sec: int = 1800) -> Generator[str, None, None]:
    """
    Converts the specified file to pdf using Libre Office CLI.
    Libre Office allows specifying the output directory and does not allow specifying the output file name.
    The output file name is generated by changing the extension to ".pdf".
    To avoid file name conflicts and additional operations the output file is written into
    a temporary directory and next yielded to the caller.
    After returning from the yield the output file and the output temp directory are removed.
    """
    if not os.path.isfile(src_fn):
        raise InputFileDoesNotExist(src_fn)
    temp_dir = tempfile.mkdtemp()
    src_fn_base = os.path.basename(src_fn)
    src_fn_base, src_ext = os.path.splitext(src_fn_base)
    out_fn = os.path.join(temp_dir, src_fn_base + '.pdf')
    try:
        additional_error_data = ""
        if src_ext.lower() in {'.tiff', '.jpg', '.jpeg', '.png'}:
            java_modules_path = get_settings().java_modules_path
            args = ['java', '-cp', f'{java_modules_path}/*',
                    'com.lexpredict.textextraction.MakePDFFromImages',
                    out_fn, src_fn]
            completed_process: CompletedProcess = _run_process(args, timeout_sec)
            raise_from_process(log, completed_process, lambda: f'Converting {src_fn} to pdf.')
            additional_error_data = render_process_msg(completed_process)
        else:
            soffice_converter = OfficeDocumentConverter()
            try:
                soffice_converter.convert(src_fn, out_fn)
            except Exception as e:
                additional_error_data = e

        if not os.path.isfile(out_fn):
            raise OutputPDFDoesNotExistAfterConversion(
                f'Unable to convert {src_fn} to pdf. Output file does not exist after conversion.'
                f'\n{additional_error_data}')
        yield out_fn

    finally:
        if os.path.isfile(out_fn):
            os.remove(out_fn)
        if os.path.isdir(temp_dir):
            os.rmdir(temp_dir)
