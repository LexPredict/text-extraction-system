from enum import Enum
from typing import Tuple, Any, Dict, List, Optional

XYWH = Tuple[float, float, float, float]

XminYminXmaxYmax = Tuple[float, float, float, float]


class Dir(Enum):
    vertical = 0
    horizontal = 1


class SelectionArea:
    def __init__(self, page: int, area: XYWH):
        self.area = area
        self.page = page

    def __str__(self):
        if not self.area:
            return 'empty'
        x, y, w, h = self.area
        return f'[x:{x}, y:{y}, w:{w}, h:{h}], page={self.page}'

    def __repr__(self):
        return self.__str__()


class PdfMarkup:
    def __init__(self,
                 char_bboxes_list: Optional[List[List[float]]],
                 pages_list: Optional[List[Dict[str, Any]]]):
        # [[x, y, w, h], [x, y, w, h], ... ]
        self.char_bboxes_list: List[List[float]] = char_bboxes_list
        # [{'number': 0, 'start': 0, 'end': 1109,
        #   'bbox': [0.0, 0.0, 595.2999877929688, 841.8900146484375]}, ...
        self.pages_list: List[Dict[str, Any]] = pages_list


def find_page_by_smb_index(pages: List[Tuple[int, int]], char_index: int) -> int:
    # finds page with start_index <= char_index < end_index
    # where each page is a tuple of (start_index, end_index)
    # returns -1 if such page is not found
    if not pages:
        return -1
    if char_index == 0:
        return 0
    if len(pages) < 10:
        for i in range(len(pages)):
            if pages[i][0] <= char_index < pages[i][1]:
                return i
        return -1

    a, b = 0, len(pages) - 1
    while b > a:
        if b - a == 1:
            if pages[a][0] <= char_index < pages[a][1]:
                return a
            if pages[b][0] <= char_index < pages[b][1]:
                return b
            return -1

        o = a + round((b - a) / 1.62)
        if char_index < pages[o][0]:
            b = o
            continue
        if char_index > pages[o][1] - 1:
            a = o
            continue
        return o
    return -1