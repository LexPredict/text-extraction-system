import os

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.ocr.rotation_detection import determine_skew, detect_rotation_dilated_rows
from text_extraction_system.pdf.pdf import extract_page_images

data_dir = os.path.join(os.path.dirname(__file__), 'data')


@with_default_settings
def test_angle1():
    fn = os.path.join(data_dir, 'deskew_goes_crazy.png')
    actual = determine_skew(fn)
    assert int(actual) == 0


@with_default_settings
def test_angle1_dilated_rows():
    fn = os.path.join(data_dir, 'deskew_goes_crazy.png')
    angle = detect_rotation_dilated_rows(fn, pre_calculated_orientation=None)
    assert int(angle) == 0


@with_default_settings
def test_angle2():
    fn = os.path.join(data_dir, 'rotated1.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        angle = determine_skew(png_fns[0])
        assert int(angle) == -6


@with_default_settings
def test_angle2_dilated_rows():
    fn = os.path.join(data_dir, 'rotated1.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        angle = detect_rotation_dilated_rows(png_fns[0], pre_calculated_orientation=None)
        assert int(angle) == -5


@with_default_settings
def test_angle3():
    fn = os.path.join(data_dir, 'rotated_small_angle.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        angle = determine_skew(png_fns[0])
        assert int(angle) == -2


@with_default_settings
def test_angle3_dilated_rows():
    fn = os.path.join(data_dir, 'rotated_small_angle.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        angle = detect_rotation_dilated_rows(png_fns[0], pre_calculated_orientation=None)
        assert int(angle) == -1


@with_default_settings
def test_angle4():
    fn = os.path.join(data_dir, 'realdoc__00121.png')
    angle = determine_skew(fn)
    assert int(angle) == -88


@with_default_settings
def test_angle4_dilated_rows():
    fn = os.path.join(data_dir, 'realdoc__00121.png')
    angle = detect_rotation_dilated_rows(fn, pre_calculated_orientation=None)
    assert int(angle) == -88


@with_default_settings
def test_angle5():
    fn = os.path.join(data_dir, 'two_vertical_lines.png')
    angle = determine_skew(fn)
    # actually should be 0 but this image will not be rotated because it does not pass OSD check
    assert int(angle) == -89


@with_default_settings
def test_angle5_dilated_rows():
    fn = os.path.join(data_dir, 'two_vertical_lines.png')
    angle = detect_rotation_dilated_rows(fn, pre_calculated_orientation=None)
    assert int(angle) == 0


@with_default_settings
def test_angle6():
    from datetime import datetime
    start = datetime.now()
    fn = os.path.join(data_dir, 'not_rotated1.png')
    angle = determine_skew(fn)
    d = datetime.now() - start
    print(f'Time: {d}')
    assert int(angle) == -1


@with_default_settings
def test_angle6_dilated_rows():
    from datetime import datetime
    start = datetime.now()
    fn = os.path.join(data_dir, 'not_rotated1.png')
    angle = detect_rotation_dilated_rows(fn, pre_calculated_orientation=None)
    d = datetime.now() - start
    print(f'Time: {d}')
    assert int(angle) == 0


@with_default_settings
def test_angle7():
    fn = os.path.join(data_dir, 'wrong_angle1.png')
    angle = determine_skew(fn)
    assert int(angle) == 2


@with_default_settings
def test_angle7_dilated_rows():
    fn = os.path.join(data_dir, 'wrong_angle1.png')
    angle = detect_rotation_dilated_rows(fn, pre_calculated_orientation=None)
    assert int(angle) == 1
