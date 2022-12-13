import os
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from logging import getLogger
from subprocess import Popen, PIPE, TimeoutExpired
from tempfile import mkdtemp
from typing import Generator, Optional, Tuple
import regex as re

from PIL import Image

from text_extraction_system.constants import TESSERACT_DEFAULT_LANGUAGE, DPI

log = getLogger(__name__)


class OCRException(Exception):
    TOO_FEW_CHARACTERS_ERROR = 'Too few characters. Skipping this page'
    pass


RE_ORIENTATION_ANGLE = re.compile(r'(?<=Orientation in degrees:)\s+\d+')
RE_ORIENTATION_CONFD = re.compile(r'(?<=Orientation confidence:)\s+[\d\.]+')


def get_page_orientation(page_image_fn: str,
                         language: str = TESSERACT_DEFAULT_LANGUAGE,
                         timeout: int = 180) -> Optional[Tuple[int, float]]:
    """
    Gets: path to the page's image
    Returns: None or (orientation_angle_degree, confidence_value)
    """
    args = ['tesseract', '--psm', '0', '-l', language]
    args.append(page_image_fn)
    with tempfile.TemporaryDirectory() as ocr_results_dir:
        ocr_results_path = os.path.join(ocr_results_dir, 'tes_output.txt')
        args.append(ocr_results_path)
        env = os.environ.copy()
        log.debug(f'Executing tesseract to check orientation: {args}')
        proc = Popen(args, env=env, stdout=PIPE, stderr=PIPE)
        try:
            _data, err = proc.communicate(timeout=timeout)
        except TimeoutExpired as te:
            proc.kill()
            _outs, _errs = proc.communicate()
            raise OCRException(f'Timeout waiting for tesseract to finish:\n{args}') from te
        if err:
            err = err.decode('utf8', 'ignore')
        if proc.returncode != 0:
            raise OCRException(f'Tesseract returned non-zero code.\n'
                               f'Command line:\n{args}\n'
                               f'Process stderr:\n{err}')
        with open(ocr_results_path + '.osd', 'r') as f_results:
            results_text = f_results.read()
    """Example result:
    Page number: 0
    Orientation in degrees: 180
    Rotate: 180
    Orientation confidence: 4.38
    Script: Latin
    Script confidence: 1.44
    """
    if not results_text:
        log.debug('tesseract --psm 0 returned 0 bytes')
        return None
    angle_strs = [m.group(0).strip() for m in RE_ORIENTATION_ANGLE.finditer(results_text)]
    if not angle_strs:
        log.debug(f'tesseract --psm 0 returned: {results_text}')
    conf_strs = [m.group(0).strip() for m in RE_ORIENTATION_CONFD.finditer(results_text)]
    if not conf_strs:
        log.debug(f'tesseract --psm 0 returned: {results_text}')
    return int(angle_strs[0]), float(conf_strs[0])


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
                '-c', 'tessedit_create_pdf=1',
                '-c', f'textonly_pdf={"1" if glyphless_text_only else "0"}']
        if language:
            args.extend(['-l', str(language)])
        args.append(page_image_fn)
        args.append(dstfn)
        env = os.environ.copy()
        log.debug(f'Executing tesseract: {args}')
        proc = Popen(args, env=env, stdout=PIPE, stderr=PIPE)
        try:
            data, err = proc.communicate(timeout=timeout)
        except TimeoutExpired as te:
            proc.kill()
            _outs, _errs = proc.communicate()
            raise OCRException(f'Timeout waiting for tesseract to finish:\n{args}') from te
        if err:
            err = err.decode('utf8', 'ignore')
        if data:
            data = data.decode('utf8', 'ignore')

        log.debug(f'{args}\nstdout:\n{data}stderr:\n{err}')
        if proc.returncode != 0:
            raise OCRException(f'Tesseract returned non-zero code.\n'
                               f'Command line:\n{args}\n'
                               f'Process stdout:\n{err}'
                               f'Process stderr:\n'
                               f'{err}')
        yield dstfn + '.pdf'
    finally:
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
        shutil.rmtree(page_dir)


@contextmanager
def rotate_image(image_fn: str,
                 angle: Optional[float] = None,
                 dpi: int = DPI,
                 align_to_closest_90: bool = True) -> Generator[str, None, None]:
    if not angle:
        yield image_fn
        return

    dst_dir = mkdtemp(prefix='deskew_')
    try:
        basename = os.path.basename(image_fn)
        dst_fn = os.path.join(dst_dir, basename)
        with Image.open(image_fn) as image_pil:  # type: Image.Image
            page_rotate: int = 90 * round(angle / 90.0)
            if align_to_closest_90:
                angle = angle - page_rotate
            image_pil = image_pil.rotate(angle, expand=False, fillcolor="white")
            image_pil.save(dst_fn, dpi=(dpi, dpi))
        yield dst_fn
    finally:
        shutil.rmtree(dst_dir)


OSD_KEYS = {
    'Page number': ('page_num', int),
    'Orientation in degrees': ('orientation', int),
    'Rotate': ('rotate', int),
    'Orientation confidence': ('orientation_conf', float),
    'Script': ('script', str),
    'Script confidence': ('script_conf', float),
}


@dataclass
class OSD:
    page_num: int
    orientation: int
    rotate: int
    orientation_conf: float
    script: Optional[str]
    script_conf: float


OSD_TOO_FEW_CHARACTERS = OSD(page_num=0, orientation=0, orientation_conf=0, script=None, script_conf=0, rotate=0)


def osd_to_dict(osd: str):
    res = dict()
    for line in osd.split('\n'):
        line_ar = line.split(':')
        if not line_ar or len(line_ar) != 2:
            continue
        tess_key_str, tess_val_str = line_ar
        (out_key, out_conv_func) = OSD_KEYS[tess_key_str.strip()]
        res[out_key] = out_conv_func(tess_val_str.strip())
    return res


def image_to_osd(page_image_fn: str, timeout: int = 180, dpi: int = DPI) -> OSD:
    proc = None
    try:
        args = ['tesseract', page_image_fn, 'stdout', '--psm', '0', '--dpi', str(dpi)]
        env = os.environ.copy()
        log.debug(f'Executing tesseract: {args}')
        proc = Popen(args, env=env, stdout=PIPE, stderr=PIPE)
        try:
            data, err = proc.communicate(timeout=timeout)
        except TimeoutExpired as te:
            proc.kill()
            outs, errs = proc.communicate()
            raise OCRException(f'Timeout waiting for tesseract to finish:\n{args}') from te

        if err:
            err = err.decode('utf8', 'ignore')
        if data:
            data = data.decode('utf8', 'ignore')

        log.debug(f'{args}\nstdout:\n{data}stderr:\n{err}')
        if proc.returncode != 0:
            if 'Too few characters' in err:
                return OSD_TOO_FEW_CHARACTERS
            else:
                raise OCRException(f'Tesseract returned non-zero code.\n'
                                   f'Command line:\n'
                                   f'{args}\n'
                                   f'Process stdout:\n'
                                   f'{err}'
                                   f'Process stderr:\n'
                                   f'{err}')

        return OSD(**osd_to_dict(data))
    finally:
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass


def orientation_and_script_detected(image_fn: str) -> bool:
    osd = image_to_osd(image_fn)

    return orientation_and_script_detected_in_osd(osd)


def orientation_and_script_detected_in_osd(osd: OSD) -> bool:
    return osd.script and osd.script_conf > 1 and osd.orientation_conf > 3
