import logging
import os
import subprocess
from contextlib import contextmanager
from subprocess import CompletedProcess
from typing import Generator

import magic

from text_extraction_system.locking.socket_lock import get_lock
from text_extraction_system.pdf.errors import OutputPDFDoesNotExistAfterConversion
from text_extraction_system.processes import render_process_msg

log = logging.getLogger(__name__)

LARGE_DATA_FILE_EXTENSIONS = ['.xml', '.xcd', '.xblr', '.html', '.htm']


def is_large_data_file(src_fn: str):
    if all([not src_fn.endswith(ext) for ext in LARGE_DATA_FILE_EXTENSIONS]):
        return False
    return os.path.getsize(src_fn) > 5 * 10 ** 6  # 5mb


def separate_filename_basename_and_extension(src_fn):
    src_fn_base = os.path.basename(src_fn)
    src_fn_base, src_ext = os.path.splitext(src_fn_base)

    # Add extension to file without it
    if not src_ext:
        filetype = magic.from_file(src_fn).lower()
        for extension in ['pdf', 'html']:
            if extension in filetype:
                os.rename(src_fn, f'{src_fn}.{extension}')
                src_fn = f'{src_fn}.{extension}'
                src_ext = extension
                break

    return src_fn, src_fn_base, src_ext


def run_process(args, timeout: int) -> CompletedProcess:
    """
    Runs subprocess
    """
    return subprocess.run(args, check=False, timeout=timeout, universal_newlines=True,
                          stderr=subprocess.PIPE, stdout=subprocess.PIPE)


@contextmanager
def prepare_large_data_file(src_fn: str,
                            out_dir: str,
                            timeout_sec: int = 1800) -> Generator[str, str, None]:
    """
    Converts the specified large data file to txt using LibreOffice CLI (lowriter tool).
    """
    if not is_large_data_file(src_fn):
        yield src_fn
    else:
        src_fn, src_fn_base, src_ext = separate_filename_basename_and_extension(src_fn)
        out_fn = os.path.join(out_dir, src_fn_base + '.txt')

        args = ['lowriter', '--headless', '--convert-to', 'txt:Text', src_fn, '--outdir', out_dir]

        with get_lock('lowriter_single_process',
                      wait_required_listener=lambda: log.info(
                          'Waiting for another conversion task to finish first...')):
            completed_process: CompletedProcess = run_process(args, timeout_sec)

        if not os.path.isfile(out_fn):
            raise OutputPDFDoesNotExistAfterConversion(
                f'Unable to convert large file {src_fn} to txt. Output file does not exist after '
                f'conversion.\n' + render_process_msg(completed_process))

        yield out_fn
