from typing import Tuple, Generator, List

import numpy as np
from imutils import contours
import cv2


class TableLocationRow:
    def __init__(self, y: float):
        self.y = y
        self.cells = 1

    def __str__(self):
        return f'x{self.cells} Y={self.y}'

    def __repr__(self):
        return self.__str__()


class TableLocation:
    ROW_Y_TOLERANCE = 10

    def __init__(self,
                 x: float,
                 y: float,
                 w: float,
                 h: float):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.rows: List[TableLocationRow] = []

    def __str__(self):
        rows_str = f', {len(self.rows)} rows' if self.rows else ''
        return f'[{self.x}, {self.y}, {self.w}, {self.h}]{rows_str}'

    def __repr__(self):
        return self.__str__()

    def point_inside(self, x: float, y: float) -> bool:
        return (self.x <= x <= (self.x + self.w)) and \
               (self.y <= y <= (self.y + self.h))

    def try_add_cell(self, c_x: float, c_y: float) -> bool:
        if not self.point_inside(c_x, c_y):
            return False
        if not self.rows:
            self.rows.append(TableLocationRow(c_y))
            return True

        row_exists = False
        for row in self.rows:
            delta_y = abs(c_y - row.y)
            if delta_y <= self.ROW_Y_TOLERANCE:
                row.cells += 1
                row_exists = True
                break
        if not row_exists:
            self.rows.append(TableLocationRow(c_y))
        return True


class TableDetector:
    def __init__(self):
        self.blur_radius_paragraph = 11
        self.gray_image = None

    def find_tables(self, image_fn: str) -> List[TableLocation]:
        self.read_image(image_fn)
        blocks = list(self.detect_paragraphs())
        return self.find_table_pivots(blocks)

    def read_image(self, image_fn: str):
        image = cv2.imread(image_fn)
        self.gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def detect_paragraphs(self) -> Generator[TableLocation, None, None]:
        blur = cv2.GaussianBlur(self.gray_image, (self.blur_radius_paragraph, self.blur_radius_paragraph), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        #kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (80, 5))
        dilate = cv2.dilate(thresh, kernel, iterations=5)
        contours, _hierarchy = cv2.findContours(dilate, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        # VISUALIZATION
        image_copy = self.gray_image.copy()
        cv2.drawContours(image=image_copy, contours=contours, contourIdx=-1, color=(0, 255, 0),
                         thickness=2, lineType=cv2.LINE_AA)
        cv2.imwrite('/home/andrey/Pictures/mix_paragraphs.png', image_copy)
        # VISUALIZATION

        for contour in contours:  # type: Tuple[float, float, float, float]
            x, y, w, h = cv2.boundingRect(contour)
            yield TableLocation(x, y, w, h)

    def find_table_pivots(self, blocks: List[TableLocation]) -> List[TableLocation]:
        # Load image, grayscale, Gaussian blur, Otsu's threshold
        blur = cv2.GaussianBlur(self.gray_image, (3, 3), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Find contours and remove text inside cells
        cnts = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        for c in cnts:
            area = cv2.contourArea(c)
            if area < 4000:
                # "erase" small contours
                cv2.drawContours(thresh, [c], -1, 0, -1)

        # Invert image
        invert = 255 - thresh

        # Find contours, sort from top-to-bottom and then sum up column/rows
        cnts = cv2.findContours(invert, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        cnts = [c for c in cnts if cv2.contourArea(c) > 200]
        (cnts, _) = contours.sort_contours(cnts, method="top-to-bottom")

        # VISUALIZE
        image_copy = self.gray_image.copy()
        cv2.drawContours(image=image_copy, contours=cnts, contourIdx=-1, color=(0, 255, 0),
                         thickness=2, lineType=cv2.LINE_AA)
        cv2.imwrite('/home/andrey/Pictures/mix_tables_rendered.png', image_copy)
        # VISUALIZE

        cell_contours = []
        for c in cnts:
            if c.shape[0] > 14:
                # this shape is too complex for a table cell
                continue
            # Find centroid
            center_moment = cv2.moments(c)
            c_x = int(center_moment["m10"] / center_moment["m00"])
            c_y = int(center_moment["m01"] / center_moment["m00"])

            for t in blocks:
                if t.try_add_cell(c_x, c_y):
                    cell_contours.append(c)

            # VISUALIZE
            cv2.circle(image_copy, (c_x, c_y), 10, (36, 180, 12), -1)
            # VISUALIZE

        # VISUALIZE
        for t in blocks:
            cv2.rectangle(image_copy, (t.x, t.y), (t.x + t.w, t.y + t.h), (192, 36, 12),
                          5 if t.rows else 1)
        cv2.drawContours(image_copy, cell_contours, -1, (0, 0, 0), 10)
        cv2.imwrite('/home/andrey/Pictures/mix_selected_table.png', image_copy)
        # VISUALIZE

        tables = [t for t in blocks if t.rows]

        return tables
