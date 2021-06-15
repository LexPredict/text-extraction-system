from typing import Tuple, List, Dict, Any
import cv2


class TableLocationCell:
    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __str__(self):
        return f'{self.x}, {self.y}, {self.w}, {self.h}'

    def __repr__(self):
        return self.__str__()

    @property
    def area(self) -> float:
        return self.w * self.h

    def get_coord(self, pivot: str) -> float:
        return self.x if pivot == 'l' else self.x + self.w if pivot == 'r' \
            else self.x + self.w / 2 if pivot == 'm' else self.y + self.h


class TableLocationCluster:
    PIVOT_TOLERANCE = 5

    def __init__(self, cell: TableLocationCell, pivot: str):
        self.cells: List[TableLocationCell] = [cell]
        self.pivot = pivot
        self.min = cell.get_coord(pivot)
        self.max = self.min

    def __str__(self):
        return f'{len(self.cells)} cells'

    def __repr__(self):
        return self.__str__()

    @property
    def area(self) -> float:
        return sum([c.area for c in self.cells]) if self.cells else 0

    def add_cell_to_cluster(self, cell: TableLocationCell) -> bool:
        p = cell.get_coord(self.pivot)
        dist = min(abs(p - self.min), abs(p - self.max))
        if dist > self.PIVOT_TOLERANCE:
            return False
        self.cells.append(cell)
        self.min = min(self.min, p)
        self.max = max(self.max, p)
        return True

    def remove_distant_cells(self):
        if len(self.cells) < 3:
            return
        mid_coord = sum([c.get_coord(self.pivot) for c in self.cells]) / len(self.cells)
        filtered = []
        for c in self.cells:
            p = c.get_coord(self.pivot)
            dist = abs(p - mid_coord)
            if dist <= self.PIVOT_TOLERANCE:
                filtered.append(c)
        self.cells = filtered

    def remove_cell(self, c: TableLocationCell):
        try:
            self.cells.remove(c)
        except ValueError:
            pass


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

        self.clusters_by_pivot: Dict[str, List[TableLocationCluster]] = {
            'l': [], 'm': [], 'r': [], 'b': []
        }
        self.column_clusters: List[TableLocationCluster] = []
        self.row_clusters: List[TableLocationCluster] = []

    def __str__(self):
        return f'[{self.x}, {self.y}, {self.w}, {self.h}]'

    def __repr__(self):
        return self.__str__()

    @property
    def area(self) -> float:
        return self.w * self.h

    def point_inside(self, x: float, y: float) -> bool:
        return (self.x <= x <= (self.x + self.w)) and \
               (self.y <= y <= (self.y + self.h))

    def cell_inside(self, cell: TableLocationCell) -> bool:
        if not self.point_inside(cell.x, cell.y):
            return False
        if not self.point_inside(cell.x + cell.w, cell.y + cell.h):
            return False
        return True

    def try_add_cell(self, cell: TableLocationCell) -> bool:
        if not self.cell_inside(cell):
            return False

        for pivot in self.clusters_by_pivot:
            clusters = self.clusters_by_pivot[pivot]
            found_cluster = False
            for cl in clusters:
                if cl.add_cell_to_cluster(cell):
                    found_cluster = True
                    break
            if not found_cluster:
                clusters.append(TableLocationCluster(cell, pivot))

        return True

    def clear_clusters(self):
        # clear clusters of duplicates (cell resides in more than one cluster) and cells
        # that are too far from the cluster's middle line
        for pivot in self.clusters_by_pivot:
            clusters = self.clusters_by_pivot[pivot]
            for c in clusters:
                c.remove_distant_cells()

            # order clusters from big to small
            clusters.sort(key=lambda cl: len(cl.cells), reverse=True)

            # and remove duplicates
            for i in range(0, len(clusters) - 1):
                for cell in clusters[i].cells:
                    for j in range(i + 1, len(clusters)):
                        clusters[j].remove_cell(cell)

        # leave the biggest column cluster list ('l' for left, 'm' for middle and 'r' for right)
        self.row_clusters = self.clusters_by_pivot['b']  # 'b' for bottom as all the cells should be bottomline
                                                         # (or baseline) aligned
        col_cl = [
            self.clusters_by_pivot['l'],
            self.clusters_by_pivot['m'],
            self.clusters_by_pivot['r']
        ]
        col_cl.sort(key=lambda cl: sum([len(cluster.cells) for cluster in cl]), reverse=True)
        self.column_clusters = col_cl[0]


class TableDetector:
    def __init__(self,
                 debug_image_path: str = ''):
        self.blur_radius_paragraph = 11
        self.column_tolerance = 5
        self.gray_image = None
        self.max_point_in_cell_contour = 9
        self.cell_contours: List[TableLocationCell] = []
        self.page_blocks: List[TableLocation] = []
        self.debug_image_path = debug_image_path

    def find_tables(self, image_fn: str) -> List[TableLocation]:
        self.read_image(image_fn)
        self.detect_paragraphs()
        return self.detect_tables_in_blocks()

    def read_image(self, image_fn: str):
        image = cv2.imread(image_fn)
        self.gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def detect_paragraphs(self):
        blur = cv2.GaussianBlur(self.gray_image, (self.blur_radius_paragraph, self.blur_radius_paragraph), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 2))

        # find cell contours
        dilate = cv2.dilate(thresh, kernel, iterations=1)
        cell_contours, _hr = cv2.findContours(dilate, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        self.build_cell_rects_from_contours(cell_contours)

        # find paragraph or table contours
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (80, 5))
        dilate = cv2.dilate(thresh, kernel, iterations=5)
        contours, _hr = cv2.findContours(dilate, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        # debug drawing
        if self.debug_image_path:
            cell_contours = [c for c in cell_contours]
            self._draw_contours('paragraphs',
                                [(contours, 3, (0, 255, 0)),
                                 (cell_contours, 1, (0, 0, 0))])
            self._draw_cells(self.cell_contours)

        for contour in contours:  # type: Tuple[float, float, float, float]
            x, y, w, h = cv2.boundingRect(contour)
            self.page_blocks.append(TableLocation(x, y, w, h))

    def build_cell_rects_from_contours(self, cell_contours: List[Any]):
        selected = []
        for c in cell_contours:
            # c.shape[0] <= self.max_point_in_cell_contour
            bounding_rect = cv2.boundingRect(c)
            contour_area = cv2.contourArea(c)
            rect_area_sz = bounding_rect[2] * bounding_rect[3]
            if rect_area_sz < contour_area * 0.75:
                continue
            selected.append(bounding_rect)
        self.cell_contours = [TableLocationCell(x, y, w, h) for x, y, w, h in selected]

    def detect_tables_in_blocks(self) -> List[TableLocation]:
        # add cells to blocks. One cell can be in several clusters
        for c in self.cell_contours:
            for block in self.page_blocks:
                if block.try_add_cell(c):
                    break
        # remove duplicates and distant cells
        for block in self.page_blocks:
            block.clear_clusters()

        # calculate: columns count, rows count, count of cells in rows or cols
        # summary area of columns and rows
        filtered_blocks = []
        for block in self.page_blocks:
            total_cells = 0
            total_area = 0.0
            row_col = [block.column_clusters, block.row_clusters]
            for clusters in row_col:
                cells = sum([len(cl.cells) for cl in clusters])
                total_cells = max(cells, total_cells)
                area = sum([cl.area for cl in clusters])
                total_area = max(area, total_area)

            # there should be more than 1 column with more than one cells in each
            columns_count = len([c for c in block.column_clusters if len(c.cells) > 1])
            if columns_count < 2:
                continue

            # total area should be greater than k*block_area
            min_area = block.area * 0.15
            if total_area < min_area:
                continue
            # total cells shouldn't be less than 5
            if total_cells < 5:
                continue
            filtered_blocks.append(block)

        self._draw_tables(filtered_blocks)

        return filtered_blocks

    def _draw_contours(self, file_suffix: str, contours: List[Tuple[List[Any], int, Tuple[int, int, int]]]):
        if not self.debug_image_path:
            return
        image_copy = self.gray_image.copy()
        for contour_list, thickness, color in contours:
            cv2.drawContours(image=image_copy, contours=contour_list, contourIdx=-1, color=color,
                             thickness=thickness, lineType=cv2.LINE_AA)
        cv2.imwrite(f'{self.debug_image_path}_{file_suffix}.png', image_copy)

    def _draw_cells(self, cells: List[TableLocationCell]):
        if not self.debug_image_path:
            return
        image_copy = self.gray_image.copy()
        for cell in cells:
            cv2.rectangle(image_copy, (cell.x, cell.y), (cell.x + cell.w, cell.y + cell.h),
                          (0, 0, 0), 2)
        cv2.imwrite(f'{self.debug_image_path}_cells.png', image_copy)

    def _draw_tables(self, tables: List[TableLocation]):
        if not self.debug_image_path:
            return
        image_copy = self.gray_image.copy()
        for table in tables:
            cv2.rectangle(image_copy, (table.x, table.y), (table.x + table.w, table.y + table.h),
                          (40, 180, 40), 5)
            clusters = table.column_clusters + table.row_clusters
            for cluster in clusters:
                for cell in cluster.cells:
                    cv2.rectangle(image_copy, (cell.x, cell.y), (cell.x + cell.w, cell.y + cell.h),
                                  (0, 0, 0), 2)
        cv2.imwrite(f'{self.debug_image_path}_tables.png', image_copy)