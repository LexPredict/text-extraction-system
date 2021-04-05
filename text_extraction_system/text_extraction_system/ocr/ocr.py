import os
import shutil
from contextlib import contextmanager
from logging import getLogger
from statistics import median
from subprocess import Popen, PIPE, TimeoutExpired
from tempfile import mkdtemp
from typing import Generator, Optional

import cv2
import deskew
import numpy as np
from PIL import Image

log = getLogger(__name__)


class OCRException(Exception):
    pass


@contextmanager
def ocr_page_to_pdf(page_image_fn: str,
                    language: str = 'eng',
                    timeout: int = 180,
                    glyphless_text_only: bool = False,
                    tesseract_page_orientation_detection: bool = False) -> Generator[str, None, None]:
    page_dir = mkdtemp(prefix='ocr_page_to_pdf_')
    proc = None
    try:
        basename = os.path.basename(page_image_fn)
        dstfn = os.path.join(page_dir, os.path.splitext(basename)[0])
        args = ['tesseract',
                '--psm', '1' if tesseract_page_orientation_detection else '3',
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


@contextmanager
def rotate_image(image_fn: str,
                 angle: Optional[float] = None,
                 dpi: int = 300,
                 align_to_closest_90: bool = True) -> Generator[str, None, None]:
    if angle is None:
        yield image_fn
        return

    dst_dir = mkdtemp(prefix='deskew_')
    try:
        basename = os.path.basename(image_fn)
        dst_fn = os.path.join(dst_dir, basename)
        with Image.open(image_fn) as image_pil:  # type: Image.Image
            page_rotate: int = 90 * round(angle / 90.0)
            w_orig, h_orig = image_pil.size
            if align_to_closest_90:
                angle = angle - page_rotate
            image_pil = image_pil.rotate(angle, expand=False, fillcolor="white")
            image_pil.save(dst_fn, dpi=(dpi, dpi))
        yield dst_fn
    finally:
        shutil.rmtree(dst_dir)


def determine_skew(image_fn: str, split_to_parts: bool = True) -> float:

    img = cv2.imread(image_fn, 0)

    # Gaussian blur with a kernel size (height, width) of 9.
    # Note that kernel sizes must be positive and odd and the kernel must be square.
    proc = cv2.GaussianBlur(img.copy(), (9, 9), 0)

    # Adaptive threshold using 11 nearest neighbour pixels
    proc = cv2.adaptiveThreshold(proc, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    # Invert colours, so gridlines have non-zero pixel values.
    # Necessary to dilate the image, otherwise will look like erosion instead.
    proc = cv2.bitwise_not(proc, proc)

    # Dilate the image to increase the size of the grid lines.
    kernel = np.array([[0., 1., 0.], [1., 1., 1.], [0., 1., 0.]], np.uint8)
    proc = cv2.dilate(proc, kernel)

    height = img.shape[0]
    width = img.shape[1]
    part_size: int = 500
    num_parts: int = round(height / part_size)

    # split image to multiple blocks, determine skew angle of each part and take median
    # this solves problem with the documents having alignment which provocates false-determining
    # of the skew for the document as a whole
    if height >= width:
        ar = [(h * part_size, (h + 1) * part_size) for h in range(num_parts)]
        images = [proc[i[0]:i[1]] for i in ar]
    else:
        ar = [(w * part_size, (w + 1) * part_size) for w in range(num_parts)]
        images = [proc[:, i[0]:i[1]] for i in ar]

    angles = [deskew.determine_skew(img) for img in images]
    res = median([a for a in angles if a is not None])
    return res
