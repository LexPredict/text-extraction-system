import logging
import os
import subprocess
import tempfile
from contextlib import contextmanager
from subprocess import CompletedProcess
from subprocess import PIPE
from typing import Generator

log = logging.getLogger(__name__)


class ConvertToPDFFailed(Exception):
    pass


class ProcessReturnedNonZeroCode(ConvertToPDFFailed):
    pass


class OutputPDFDoesNotExistAfterConversion(ConvertToPDFFailed):
    pass


class InputFileDoesNotExist(ConvertToPDFFailed):
    pass


@contextmanager
def convert_to_pdf(src_fn: str) -> Generator[str, None, None]:
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
            args = ['img2pdf', src_fn, '-o', out_fn]
        else:
            args = ['soffice',
                    '--headless',
                    '--invisible',
                    '--nodefault',
                    '--view',
                    '--nolockcheck',
                    '--nologo',
                    '--norestore',
                    '--nofirststartwizard',
                    '--convert-to',
                    'pdf',
                    src_fn,
                    '--outdir',
                    temp_dir
                    ]
        completed_process: CompletedProcess = subprocess.run(args,
                                                             check=False,
                                                             timeout=600,
                                                             universal_newlines=True,
                                                             stderr=PIPE,
                                                             stdout=PIPE)

        msg = f'Command line:\n' \
              f'{args}'

        if completed_process.stdout:
            msg += f'Process stdout:\n' \
                   f'===========================\n' \
                   f'{completed_process.stdout}\n' \
                   f'===========================\n'
        if completed_process.stderr:
            msg += f'Process stderr:\n' \
                   f'===========================\n' \
                   f'{completed_process.stderr}\n' \
                   f'===========================\n'

        if completed_process.returncode != 0:
            raise ProcessReturnedNonZeroCode(f'Unable to convert {src_fn} to pdf. '
                                             f'Process returned non-zero code.\n'
                                             + msg)
        elif not os.path.isfile(out_fn):
            raise OutputPDFDoesNotExistAfterConversion(f'Unable to convert {src_fn} to pdf. '
                                                       f'Output file does not exist after conversion.\n' + msg)
        else:
            log.debug(msg)

        yield out_fn

    finally:
        if os.path.isfile(out_fn):
            os.remove(out_fn)
        if os.path.isdir(temp_dir):
            os.rmdir(temp_dir)
