import os

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.ocr.rotation_detection import determine_rotation, \
    detect_rotation_dilated_rows, WeightedAverage
from text_extraction_system.pdf.pdf import extract_page_images

data_dir = os.path.join(os.path.dirname(__file__), 'data')


def test_weighted_angle_simple():
    wa = WeightedAverage()
    wa.values = [(0, 10), (10, 990)]
    assert wa.get_weighted_avg(0) == 9.9

    wa = WeightedAverage()
    wa.values = [(1.5, 2)]
    assert wa.get_weighted_avg(0) == 1.5
    assert wa.get_weighted_avg(0.2) == 1.5


def test_weighted_angle_skip_tails():
    wa_1 = WeightedAverage([(1, 10), (5, 500), (6, 500), (100, 10)])
    a_0 = round(wa_1.get_weighted_avg(0), 1)
    a_1 = round(wa_1.get_weighted_avg(0.1), 1)

    wa_2 = WeightedAverage([(1, 0.01), (5, 0.49), (6, 0.49), (100, 0.01)])
    a_2 = round(wa_2.get_weighted_avg(0.1), 1)

    wa_3 = WeightedAverage([(5, 0.4), (6, 0.4)])
    a_3 = round(wa_3.get_weighted_avg(0), 1)

    assert a_3 == 5.5
    assert a_0 > a_1  # as we cut a fat tail
    assert a_1 == a_2
    assert a_1 == a_3


def test_weighted_angle_short_fat_tail():
    wa = WeightedAverage([(1, 11), (5, 1), (6, 100)])
    a = round(wa.get_weighted_avg(0.1), 3)
    assert a == 5.991

    a_2 = round(wa.get_weighted_avg(0), 3)
    assert a_2 < a


@with_default_settings
def test_angle1():
    fn = os.path.join(data_dir, 'deskew_goes_crazy.png')
    actual = determine_rotation(fn).angle
    assert int(actual) == 0


@with_default_settings
def test_angle1_dilated_rows():
    fn = os.path.join(data_dir, 'deskew_goes_crazy.png')
    angle = detect_rotation_dilated_rows(fn, pre_calculated_orientation=None).angle
    assert int(angle) == 0


@with_default_settings
def test_angle2():
    fn = os.path.join(data_dir, 'rotated1.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        angle = determine_rotation(png_fns[0]).angle
        assert int(angle) == -6


@with_default_settings
def test_angle2_dilated_rows():
    fn = os.path.join(data_dir, 'rotated1.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        angle = detect_rotation_dilated_rows(png_fns[0], pre_calculated_orientation=None).angle
        assert int(angle) == -5


@with_default_settings
def test_angle3():
    fn = os.path.join(data_dir, 'rotated_small_angle.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        angle = determine_rotation(png_fns[0]).angle
        assert int(angle) == -2


@with_default_settings
def test_angle3_dilated_rows():
    fn = os.path.join(data_dir, 'rotated_small_angle.pdf')
    with extract_page_images(fn, 1, 1) as png_fns:
        angle = detect_rotation_dilated_rows(png_fns[0], pre_calculated_orientation=None).angle
        assert int(angle) == -1


@with_default_settings
def test_angle5():
    fn = os.path.join(data_dir, 'two_vertical_lines.png')
    angle = determine_rotation(fn).angle
    # actually should be 0 but this image will not be rotated because it does not pass OSD check
    assert int(angle) == -89


@with_default_settings
def test_angle5_dilated_rows():
    fn = os.path.join(data_dir, 'two_vertical_lines.png')
    angle = detect_rotation_dilated_rows(fn, pre_calculated_orientation=None).angle
    assert int(angle) == 0
