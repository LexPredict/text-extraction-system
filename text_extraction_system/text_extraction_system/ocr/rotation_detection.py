import os
import tempfile
from collections import Counter
from enum import Enum
from statistics import median
from typing import Optional, Tuple, List

import cv2
import deskew
from PIL import Image as PilImage

from text_extraction_system.ocr.ocr import image_to_osd, orientation_and_script_detected_in_osd

# used in detect_rotation_dilated_rows() - "ideal" image size for resizing code
SKEW_IMAGE_DETECT_TARGET_SIZE = 960, 1200

# used in detect_rotation_dilated_rows() to blur the image before applying binary filter
IMAGE_BLUR_RADIUS = 11

# used in determine_skew_dilated_rows() - min image dimension after resizing
MIN_IMAGE_DIMENSION = 200

# used in detect_rotation_most_frequent() - size of the image subpart
IMAGE_PART_SIZE = 500


class PageRotationStatus:
    def __init__(self,
                 angle: float = 0,
                 occupied_area_percent: Optional[float] = None):
        self.angle = angle
        self.occupied_area_percent = occupied_area_percent

    def __str__(self):
        return f'{self.angle:.2f} grad, {self.occupied_area_percent:.2f}% area'


def detect_rotation_dilated_rows(image_fn: str, pre_calculated_orientation: Optional[int] = None) -> PageRotationStatus:
    filename = None
    try:
        if pre_calculated_orientation is not None:
            orientation = pre_calculated_orientation
        else:
            osd = image_to_osd(image_fn)
            orientation = osd.orientation if orientation_and_script_detected_in_osd(osd) else 0

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
        total_cont_area = 0
        weighted_ang = WeightedAverage()

        for c in contours:
            r = cv2.minAreaRect(c)
            rect_area = r[1][0] * r[1][1]
            total_cont_area += rect_area
            angle = r[-1]
            if angle < -45:
                angle = angle + 90
            angle = norm_angle(orientation + angle)
            weighted_ang.add(angle, rect_area)

        img_size = gray.shape[1] * gray.shape[0]
        text_share = round(100 * total_cont_area / img_size, 2)
        weighted_angle = weighted_ang.get_weighted_avg(0.1)
        weighted_angle = round(weighted_angle, 1)
        return PageRotationStatus(weighted_angle, text_share)
    finally:
        if filename:
            os.remove(filename)


def detect_rotation_using_skewlib(image_fn: str) -> PageRotationStatus:
    proc = cv2.imread(image_fn, 0)
    angle = deskew.determine_skew(proc)
    return PageRotationStatus(angle)


def detect_rotation_most_frequent(image_fn: str) -> PageRotationStatus:
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
        return PageRotationStatus(most_frequent[0])
    else:
        # otherwise use median angle - which is usually good but not the best
        return PageRotationStatus(median(angles))


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


def determine_rotation(image_fn: str,
                       detecting_method: RotationDetectionMethod = RotationDetectionMethod.DESKEW,
                       max_diff_from_closest_90: float = 10) -> PageRotationStatus:
    # default method is set to DESKEW (plain deskew lib) because it works on
    # larger amount of cases including images rotated on ~~90 degrees
    # (but is slower)
    rs = _methods[detecting_method](image_fn)
    angle = norm_angle(rs.angle)

    if abs(angle - 90 * round(angle / 90)) > max_diff_from_closest_90:
        angle = 0
    rs.angle = angle
    return rs


class WeightedAverage:
    # The class calculates weighted average of "v" for tuples [v, w]
    # where "w" is the weight.
    # The class also cuts q (0 <= q < 0.5) share from both head and tail of the list
    def __init__(self, values: Optional[List[Tuple[float, float]]] = None):
        self.values: List[Tuple[float, int]] = values or []

    def add(self, val: float, count: int):
        self.values.append((val, count))

    def get_weighted_avg(self, tails_skip_quantile: float = 0) -> float:
        """
        Let tails_skip_quantile = 0.1
        values = [(1, 10), (5, 500), (6, 500), (100, 10)]
        Note: the values are sorted.
        We may consider 10% of extremely low values and 10% of extremely high values fluctuations.

        First, we replace weights with weight shares:
        values = [(1, 0.01), (5, 0.49), (6, 0.49), (100, 0.01)]

        Now we're cutting the head 0.1 share of weighted values.
        We totally neglect the first tuple (1, 0.01) because it's weight is below 0.1
        We also "cut" part of the second tuple: (5, 0.49). That means we simply decrement its weight:
        0.49 => (0.49 + 0.1) /* accumulated weight */ - 0.1 /* tails_skip_quantile */
             =>  0.4
        So the second tuple is now (5, 0.4)

        That means get_weighted_avg([(1, 10), (5, 500), (6, 500), (100, 10)], 0.1) gives us the same as
                   get_weighted_avg([(1, 0.01), (5, 0.49), (6, 0.49), (100, 0.01)], 0.1) or
                   get_weighted_avg([(5, 0.4), (6, 0.4)], 0.0)
        """
        if not self.values:
            return 0
        tot_weight = sum([w for _, w in self.values])
        if not tot_weight:
            return 0
        val_s = [(v, w / tot_weight) for v, w in self.values]

        if not tails_skip_quantile or len(self.values) < 3:
            return sum([v * s for v, s in val_s])

        # we cut N% of extremely low and N% of extremely high values
        val_s.sort(key=lambda v: v[0])
        head_s, tail_s = tails_skip_quantile, 1 - tails_skip_quantile
        body_s = 1 - tails_skip_quantile * 2
        s = 0
        passed_head, passed_tail = False, False

        sum_val = 0
        for v, w in val_s:
            s += w
            if not passed_head:
                if s < head_s:
                    continue
                w = s - head_s
                passed_head = True
            if s > tail_s:
                ex_part = s - tail_s
                w -= ex_part
                passed_tail = True

            share = w / body_s
            sum_val += v * share
            if passed_tail:
                break
        return sum_val
