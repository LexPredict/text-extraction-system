import logging
import os
import shutil
import subprocess
from subprocess import CompletedProcess
from tempfile import mkdtemp
from typing import Optional

from text_extraction_system.config import get_settings
from text_extraction_system.pdf.pdf import raise_from_pdfbox_error_messages
from text_extraction_system.processes import raise_from_process

log = logging.getLogger(__name__)


def remove_ocr_layer(pdf_file_name: str,
                     pdf_password: Optional[str] = None,
                     timeout_sec: int = 1800):
    temp_dir = mkdtemp()
    try:
        dst_pdf_fn = os.path.join(temp_dir, os.path.basename(pdf_file_name))

        java_modules_path = get_settings().java_modules_path
        args = ['java', '-cp', f'{java_modules_path}/*',
                'com.lexpredict.textextraction.RemovePdfText',
                '-orig', pdf_file_name,
                '-dst', dst_pdf_fn]

        if pdf_password:
            args += ['--password', pdf_password]

        completed_process: CompletedProcess = subprocess.run(
            args,
            check=False,
            timeout=timeout_sec,
            universal_newlines=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        raise_from_process(log, completed_process,
                           process_title=lambda: f"Couldn't remove OCR layers from {pdf_file_name}")

        raise_from_pdfbox_error_messages(completed_process)

        shutil.move(dst_pdf_fn, pdf_file_name)
    except Exception:
        raise
    finally:
        shutil.rmtree(temp_dir)