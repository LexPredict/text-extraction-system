import os
from math import floor

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.ocr.ocr import determine_skew, RotationDetectionMethod
from text_extraction_system.pdf.pdf import extract_page_images

data_dir = os.path.join(os.path.dirname(__file__), 'data')


@with_default_settings
def test_angle1():
    fn = os.path.join(data_dir, 'deskew_goes_crazy.png')
    actual = determine_skew(fn)

    assert abs(actual) < 10


@with_default_settings
def test_angle2():
    fn = os.path.join(data_dir, 'rotated1.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        angle = determine_skew(png_fns[0])
        assert 5 < abs(angle) < 7


@with_default_settings
def test_angle3():
    fn = os.path.join(data_dir, 'rotated_small_angle.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        angle = determine_skew(png_fns[0])
        assert floor(abs(angle)) == 2


@with_default_settings
def test_angle4():
    fn = os.path.join(data_dir, 'realdoc__00121.png')
    angle = determine_skew(fn)
    assert floor(abs(angle)) == 88


@with_default_settings
def test_angle5():
    fn = os.path.join(data_dir, 'picture_angles__00003.png')
    angle = determine_skew(fn, detecting_method=RotationDetectionMethod.DILATED_ROWS)
    assert floor(abs(angle)) == 0

