import itertools
import math
import os
from typing import Tuple, Optional, List
from unittest import TestCase
import regex as re
from text_extraction_system.ocr import rotation_detection


class DetectionParams:
    def __init__(self,
                 blur_size: Optional[int] = None,
                 image_size: Optional[Tuple[int, int]] = None):
        self.blur_size = blur_size
        self.image_size = image_size

    def __str__(self):
        s_blur = f'blur: {self.blur_size} ' if self.blur_size else ''
        s_image_size = f'image size: {self.image_size}' if self.image_size else ''
        return s_blur + s_image_size

    def __repr__(self):
        return self.__str__()

    @classmethod
    def combine(cls, items: Tuple['DetectionParams']) -> 'DetectionParams':
        p = DetectionParams(items[0].blur_size, items[0].image_size)
        for item in items[1:]:
            if p.blur_size is None:
                p.blur_size = item.blur_size
            if p.image_size is None:
                p.image_size = item.image_size
        return p

    def apply_params(self) -> 'DetectionParams':
        old_params = DetectionParams(rotation_detection.IMAGE_BLUR_RADIUS,
                                     rotation_detection.SKEW_IMAGE_DETECT_TARGET_SIZE)
        if self.blur_size:
            rotation_detection.IMAGE_BLUR_RADIUS = self.blur_size
        if self.image_size:
            rotation_detection.SKEW_IMAGE_DETECT_TARGET_SIZE = self.image_size
        return old_params


class Testrotation_detection(TestCase):
    """
    One can print a PDF file to images with the command
    gs -dBATCH -dNOPAUSE -sOutputFile=<out folder>/print-to-file.%d.png \
       -sDEVICE=pnggray -r600 -dDownScaleFactor=3 <src file path.pdf>
    """

    # this folder is to be set before running training method
    IMAGE_FOLDER = ''

    def non_test_train(self):
        # don't forget to "-"
        y = [1.8, -1.86, -0.33, 0, -0.27,  # page 5
             0.36, -0.52, 0.5, -0.7, 0.55,  # page 10,
             -0.5, 0.6, -0.6, 0.93, -0.93,  # page 15
             0.93, -0.55, 0.6, -0.6, 0.53]
        y = [-y for y in y]

        ptrs_blur = [DetectionParams(i) for i in range(5, 16, 2)]
        ptrs_size = [DetectionParams(None, (int(800 * i / 10), int(1000 * i / 10))) for i in range(5, 27)]

        x: List[DetectionParams] = []
        for det_ptrs in itertools.product(ptrs_blur, ptrs_size):
            p = DetectionParams.combine(det_ptrs)
            x.append(p)

        file_names = self.get_file_names()

        print(f'Running {len(x)} tests for {len(file_names)} files ...')
        default_y_hat = self.get_y_hat(file_names, DetectionParams())
        default_error = self.calc_error(y, default_y_hat)
        error, best_index = default_error, -1
        for i in range(len(x)):
            y_hat = self.get_y_hat(file_names, x[i])
            error_i = self.calc_error(y, y_hat)
            if error_i < error:
                best_index = i
                error = error_i
            print(f'{i+1} of {len(x)} tests completed')

        print(f'Default detection error: {default_error}, resulting error: {error}')
        if best_index >= 0:
            print(f'Best detecting params: {x[best_index]}')
        else:
            print(f'No better detecting params found')

    def get_file_names(self) -> List[str]:
        file_names = [f for f in os.listdir(self.IMAGE_FOLDER) if os.path.isfile(os.path.join(self.IMAGE_FOLDER, f))]
        reg_num = re.compile(r'\d+')
        file_nums = [(f, [int(m.group()) for m in reg_num.finditer(f)][0]) for f in file_names]
        file_nums.sort(key=lambda f: f[1])
        return [f for f, _num in file_nums][:20]

    def calc_error(self, y: List[float], y_hat: List[float]) -> float:
        return sum([math.pow((y[i] - y_hat[i]), 2) for i in range(len(y))])

    def get_y_hat(self,
                  file_names: List[str],
                  det_ptrs: DetectionParams) -> List[float]:
        y_hat = []
        old_params = det_ptrs.apply_params()
        try:
            for file_name in file_names:
                file_path = os.path.join(self.IMAGE_FOLDER, file_name)
                angle = rotation_detection.detect_rotation_dilated_rows(file_path)
                y_hat.append(angle)
        finally:
            old_params.apply_params()
        return y_hat
