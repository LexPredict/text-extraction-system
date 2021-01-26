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
                   soffice_single_process_locking: bool = True,
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
        if src_ext.lower() in {'.tiff', '.jpg', '.jpeg', '.png'}:
            java_modules_path = get_settings().java_modules_path
            args = ['java', '-cp', f'{java_modules_path}/*',
                    'com.lexpredict.textextraction.MakePDFFromImages',
                    out_fn, src_fn]
            completed_process: CompletedProcess = _run_process(args, timeout_sec)
        else:
            args = ['soffice', '--headless', '--invisible', '--nodefault', '--view', '--nolockcheck',
                    '--nologo', '--norestore', '--nofirststartwizard', '--convert-to', 'pdf', src_fn,
                    '--outdir', temp_dir]

            # We are using "soffice" (Libre Office) to "print" any document to pdf
            # and it seems not allowing running more than one copy of the process in some environments.
            # The following is a workaround mostly for in-container usage.
            # There is no guaranty that it will work on a dev machine when there is an "soffice" process
            # started by some other app/user.
            if soffice_single_process_locking:
                with get_lock('soffice_single_process',
                              wait_required_listener=
                              lambda: log.info('Waiting for another conversion task to finish first...')):
                    completed_process: CompletedProcess = _run_process(args, timeout_sec)
            else:
                completed_process: CompletedProcess = _run_process(args, timeout_sec)

        raise_from_process(log, completed_process, lambda: f'Converting {src_fn} to pdf.')

        if not os.path.isfile(out_fn):
            raise OutputPDFDoesNotExistAfterConversion(f'Unable to convert {src_fn} to pdf. '
                                                       f'Output file does not exist after conversion.\n'
                                                       + render_process_msg(completed_process))
        yield out_fn

    finally:
        if os.path.isfile(out_fn):
            os.remove(out_fn)
        if os.path.isdir(temp_dir):
            os.rmdir(temp_dir)
