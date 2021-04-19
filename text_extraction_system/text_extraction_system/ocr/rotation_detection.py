import os
import tempfile
from collections import Counter
from enum import Enum
from statistics import median
from typing import Optional

import cv2
import deskew
from PIL import Image as PilImage

from text_extraction_system.ocr.ocr import image_to_osd

# used in detect_rotation_dilated_rows() - "ideal" image size for resizing code
SKEW_IMAGE_DETECT_TARGET_SIZE = 960, 1200

# used in detect_rotation_dilated_rows() to blur the image before applying binary filter
IMAGE_BLUR_RADIUS = 11

# used in determine_skew_dilated_rows() - min image dimension after resizing
MIN_IMAGE_DIMENSION = 200

# used in detect_rotation_most_frequent() - size of the image subpart
IMAGE_PART_SIZE = 500


def detect_rotation_dilated_rows(image_fn: str, pre_calculated_orientation: Optional[int] = None) -> Optional[float]:
    filename = None
    try:
        if pre_calculated_orientation is not None:
            orientation = pre_calculated_orientation
        else:
            osd = image_to_osd(image_fn)
            orientation = osd.orientation if osd.orientation_conf > 1 else 0

        if orientation:
            _new_file, filename = tempfile.mkstemp('.png')
            src_image: PilImage.Image = PilImage.open(image_fn)
            src_image.rotate(orientation, expand=True).save(filename)
            image_fn = filename

        # Prep image, copy, convert to gray scale, blur, and threshold
        gray = cv2.imread(image_fn, 0)
        # ksize (9, 9) is OK... (11, 11) is maybe even better
        blur = cv2.GaussianBlur(gray, (IMAGE_BLUR_RADIUS, IMAGE_BLUR_RADIUS), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        # Apply dilate to merge text into meaningful lines/paragraphs.
        # Use larger kernel on X axis to merge characters into single line, cancelling out any spaces.
        # But use smaller kernel on Y axis to separate between different blocks of text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        dilate = cv2.dilate(thresh, kernel, iterations=5)

        # Find all contours
        contours, hierarchy = cv2.findContours(dilate, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        angles_to_areas = dict()
        max_area = -1
        max_area_angle = 0
        for c in contours:
            angle = cv2.minAreaRect(c)[-1]
            if angle < -45:
                angle = angle + 90
            angle = norm_angle(orientation + angle)
            angle = round(angle * 10) / 10
            area = angles_to_areas.get(angle) or 0
            area += cv2.contourArea(c)
            angles_to_areas[angle] = area
            if max_area < area:
                max_area = area
                max_area_angle = angle

        return max_area_angle
    finally:
        if filename:
            os.remove(filename)


def detect_rotation_using_skewlib(image_fn: str) -> Optional[float]:
    proc = cv2.imread(image_fn, 0)
    return deskew.determine_skew(proc)


def detect_rotation_most_frequent(image_fn: str) -> Optional[float]:
    proc = cv2.imread(image_fn, 0)
    height, width = proc.shape
    part_size: int = IMAGE_PART_SIZE
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
    angles = [a for a in angles if a is not None]
    if not angles:
        return None

    freqs = Counter(angles)
    most_frequent = sorted(freqs.items(), key=lambda it: it[1], reverse=True)[0]
    if most_frequent[1] > 1:
        # if at least some angle repeats - return the one with the max frequency
        return most_frequent[0]
    else:
        # otherwise use median angle - which is usually good but not the best
        return median(angles)


def norm_angle(angle_degrees: Optional[float]) -> Optional[float]:
    if angle_degrees is None:
        return None
    angle_degrees = angle_degrees % 360
    angle_degrees = angle_degrees if angle_degrees < 180 else angle_degrees - 360
    return angle_degrees


class RotationDetectionMethod(int, Enum):
    DESKEW = 1
    TILE_DESKEW = 2
    DILATED_ROWS = 3


_methods = {
    RotationDetectionMethod.DESKEW: detect_rotation_using_skewlib,
    RotationDetectionMethod.TILE_DESKEW: detect_rotation_most_frequent,
    RotationDetectionMethod.DILATED_ROWS: detect_rotation_dilated_rows
}


def determine_skew(image_fn: str,
                   detecting_method: RotationDetectionMethod
                   = RotationDetectionMethod.DESKEW,
                   max_diff_from_closest_90: float = 10) -> Optional[float]:
    # default method is set to DESKEW (plain deskew lib) because it works on
    # larger amount of cases including images rotated on ~~90 degrees
    # (but is slower)
    angle = _methods[detecting_method](image_fn)
    angle = norm_angle(angle)

    if abs(angle - 90 * round(angle / 90)) <= max_diff_from_closest_90:
        return angle
    else:
        return None
