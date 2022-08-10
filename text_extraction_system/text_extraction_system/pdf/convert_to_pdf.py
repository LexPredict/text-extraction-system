import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from subprocess import CompletedProcess
from typing import Generator

from text_extraction_system.config import get_settings
from text_extraction_system.locking.socket_lock import get_lock
from text_extraction_system.pdf.errors import InputFileDoesNotExist, \
    OutputPDFDoesNotExistAfterConversion
from text_extraction_system.pdf.utils import separate_filename_basename_and_extension, \
    run_process, prepare_large_data_file
from text_extraction_system.processes import raise_from_process, render_process_msg

log = logging.getLogger(__name__)

SOFFICE_CALL_BASE_ARGUMENTS = ['--headless', '--invisible', '--nodefault', '--view',
                               '--nolockcheck', '--nologo', '--norestore', '--nofirststartwizard', ]


def convert_image_to_pdf(src_fn: str,
                         out_fn: str,
                         timeout_sec: int = 1800) -> CompletedProcess:
    """
    Converts image to pdf file using custom Java solution
    """
    args = ['java', '-cp', f'{get_settings().java_modules_path}/*',
            'com.lexpredict.textextraction.MakePDFFromImages',
            out_fn, src_fn]
    return run_process(args, timeout_sec)


def soffice_convert_to_pdf(src_fn: str,
                           directory: str,
                           soffice_single_process_locking: bool = True,
                           timeout_sec: int = 1800) -> CompletedProcess:
    """
    Converts image to pdf file using custom Java solution
    """
    with prepare_large_data_file(src_fn, directory) as prepared_fn:
        args = ['soffice', *SOFFICE_CALL_BASE_ARGUMENTS,
                '--convert-to', 'pdf',
                prepared_fn,
                '--outdir', directory]

        # Soffice does not allow running multiple copies of the process in environment.
        # The following is a workaround mostly for in-container usage.
        if soffice_single_process_locking:
            with get_lock('soffice_single_process',
                          wait_required_listener=lambda: log.info(
                              'Waiting for another conversion task to finish first...')):
                return run_process(args, timeout_sec)
        return run_process(args, timeout_sec)


@contextmanager
def convert_to_pdf(src_fn: str,
                   soffice_single_process_locking: bool = True,
                   timeout_sec: int = 1800) -> Generator[str, None, None]:
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
    src_fn, src_fn_base, src_ext = separate_filename_basename_and_extension(src_fn, temp_dir)
    out_fn = os.path.join(temp_dir, src_fn_base + '.pdf')

    # Bypass pdf file
    if src_ext == 'pdf':
        return src_fn

    try:
        if src_ext.lower() in {'.tiff', '.jpg', '.jpeg', '.png'}:
            completed_process = convert_image_to_pdf(src_fn, out_fn, timeout_sec)
        else:
            completed_process = soffice_convert_to_pdf(src_fn, temp_dir,
                                                       soffice_single_process_locking, timeout_sec)
        raise_from_process(log, completed_process, lambda: f'Converting {src_fn} to pdf.')

        if not os.path.isfile(out_fn):
            raise OutputPDFDoesNotExistAfterConversion(
                f'Unable to convert {src_fn} to pdf. Output file does not exist after conversion.\n'
                + render_process_msg(completed_process))
        yield out_fn
    finally:
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)
