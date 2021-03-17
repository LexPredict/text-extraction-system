import os
import shutil
from contextlib import contextmanager
from logging import getLogger
from subprocess import Popen, PIPE, TimeoutExpired
from tempfile import mkdtemp
from typing import Generator

log = getLogger(__name__)


class OCRException(Exception):
    pass


@contextmanager
def ocr_page_to_pdf(page_image_fn: str,
                    language: str = 'eng',
                    timeout: int = 60,
                    glyphless_text_only: bool = False) -> Generator[str, None, None]:
    page_dir = mkdtemp(prefix='ocr_page_to_pdf_')
    proc = None
    try:
        basename = os.path.basename(page_image_fn)
        dstfn = os.path.join(page_dir, os.path.splitext(basename)[0])
        args = ['tesseract',
                '--psm', '1',
                '-l', str(language),
                '-c', 'tessedit_create_pdf=1',
                '-c', f'textonly_pdf={"1" if glyphless_text_only else "0"}',
                page_image_fn,
                dstfn]
        env = os.environ.copy()
        log.debug(f'Executing tesseract: {args}')
        proc = Popen(args, env=env, stdout=PIPE, stderr=PIPE)
        try:
            data, err = proc.communicate(timeout=timeout)
            yield dstfn + '.pdf'
        except TimeoutExpired as te:
            proc.kill()
            outs, errs = proc.communicate()
            raise OCRException(f'Timeout waiting for tesseract to finish:\n{args}') from te
        if data:
            data = data.decode('utf8', 'ignore')

        if err:
            err = err.decode('utf8', 'ignore')
        if data:
            data = data.decode('utf8', 'ignore')

        log.debug(f'{args}\nstdout:\n{data}stderr:\n{err}')
        if proc.returncode != 0:
            raise OCRException(f'Tesseract returned non-zero code.\n'
                               f'Command line:\n'
                               f'{args}\n'
                               f'Process stdout:\n'
                               f'{err}'
                               f'Process stderr:\n'
                               f'{err}')
    finally:
        if proc is not None:
            try:
                proc.kill()
            except:
                pass
        shutil.rmtree(page_dir)
