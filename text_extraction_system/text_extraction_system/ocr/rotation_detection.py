import math
import os
import tempfile
from collections import Counter
from enum import Enum
from statistics import median
from typing import Optional

import cv2
import deskew
from PIL import Image as PilImage
from PIL import ImageOps

# used in detect_rotation_dilated_rows() - "ideal" image size for resizing code
SKEW_IMAGE_DETECT_TARGET_SIZE = 960, 1200

# used in detect_rotation_dilated_rows() to blur the image before applying binary filter
IMAGE_BLUR_RADIUS = 5

# used in determine_skew_dilated_rows() - min image dimension after resizing
MIN_IMAGE_DIMENSION = 200

# used in detect_rotation_most_frequent() - size of the image subpart
IMAGE_PART_SIZE = 500


def detect_rotation_dilated_rows(image_fn: str) -> Optional[float]:
    # make file grayscale and not too large
    src_image = PilImage.open(image_fn)
    img_gray: PilImage = ImageOps.grayscale(src_image)
    min_size = min(img_gray.size[0], img_gray.size[1])
    img_area = img_gray.size[0] * img_gray.size[1]
    scale_k = math.pow(1.0 * (SKEW_IMAGE_DETECT_TARGET_SIZE[0] *
                              SKEW_IMAGE_DETECT_TARGET_SIZE[1]) / img_area, 0.5)
    new_min_size = int(min_size * scale_k)
    new_min_size = max(new_min_size, min(min_size, MIN_IMAGE_DIMENSION))
    scale_k = new_min_size / min_size
    new_size = int(scale_k * img_gray.size[0]), int(scale_k * img_gray.size[1])
    img_gray.thumbnail(new_size, PilImage.ANTIALIAS)

    _new_file, filename = tempfile.mkstemp('.png')
    try:
        img_gray.save(filename)
        # Prep image, copy, convert to gray scale, blur, and threshold
        gray = cv2.imread(filename, 0)
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
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        # Find largest contour and surround in min area box
        largestContour = contours[0]
        minAreaRect = cv2.minAreaRect(largestContour)

        # Determine the angle. Convert it to the value that was originally used to obtain skewed image
        angle = minAreaRect[-1]
        if angle < -45:
            angle = 90 + angle
        return 1.0 * angle
    finally:
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


class RotationDetectionMethod(str, Enum):
    DESKEW = 'deskew'
    TILE_DESKEW = 'tile_deskew'
    DILATED_ROWS = 'dilated_rows'


def determine_skew(image_fn: str,
                   detecting_method: RotationDetectionMethod
                   = RotationDetectionMethod.DESKEW) -> Optional[float]:
    # default method is set to DESKEW (plain deskew lib) because it works on
    # larger amount of cases including images rotated on ~~90 degrees
    # (but is slower)
    if detecting_method == RotationDetectionMethod.TILE_DESKEW:
        return detect_rotation_most_frequent(image_fn)
    if detecting_method == RotationDetectionMethod.DILATED_ROWS:
        return detect_rotation_dilated_rows(image_fn)
    return detect_rotation_using_skewlib(image_fn)
