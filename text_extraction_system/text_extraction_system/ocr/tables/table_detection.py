from typing import Tuple, List, Dict, Any, Optional
import cv2


class TableDetectorSettings:
    def __init__(self,
                 blur_radius_paragraph: int = 11,
                 column_tolerance: int = 5,
                 max_point_in_cell_contour: int = 9,
                 pivot_tolerance: int = 5,
                 row_y_tolerance: int = 10,
                 max_image_dimension: int = 1200,
                 contour_square_area_share: float = 0.75,
                 paragraph_morph_shape_sz: Tuple[int, int] = (80, 5),
                 cell_morph_shape_sz: Tuple[int, int] = (50, 2),
                 paragraph_dilate_iterations: int = 5,
                 cell_dilate_iterations: int = 1,
                 min_columns_in_table: int = 2,
                 cell_area_to_table_area: float = 0.15,
                 min_total_cells_in_table: int = 5,
                 max_column_span_part: float = 0.3):
        # we make original image grayscale and then blur before making the image contrast (black and white)
        # and then we detect contours by cv2 library functions
        self.blur_radius_paragraph = blur_radius_paragraph
        self.column_tolerance = column_tolerance
        self.max_point_in_cell_contour = max_point_in_cell_contour
        # we join cell contours in a column / a row (candidate) if the cells' coordinate
        # (left or middle or right for columns, bottom for rows) vary within the provided range (pixels)
        self.pivot_tolerance = pivot_tolerance
        self.row_y_tolerance = row_y_tolerance
        # if one of the source image's dimensions larger than N the image is scaled down
        self.max_image_dimension = max_image_dimension
        # a contour is considered "rectangle" if its area size is not less than k * box_size,
        # where box_size is the area size for the surrounding box
        self.contour_square_area_share = contour_square_area_share
        # the shape's (rectangle) size for dilate transformation for paragraphs
        self.paragraph_morph_shape_sz = paragraph_morph_shape_sz
        # the shape's (rectangle) size for dilate transformation for cells
        self.cell_morph_shape_sz = cell_morph_shape_sz
        # count of iterations while dilating text contours to determine paragraphs
        self.paragraph_dilate_iterations = paragraph_dilate_iterations
        # count of iterations while dilating text contours to determine cells
        self.cell_dilate_iterations = cell_dilate_iterations
        # a table should contain at least N columns to be considered table
        self.min_columns_in_table = min_columns_in_table
        # table cells should occupy at least k of the table's whole area
        self.cell_area_to_table_area = cell_area_to_table_area
        # table should contain at least N cells
        self.min_total_cells_in_table = min_total_cells_in_table
        # two columns overlap if their common X-projection part is greater than k * min_c_w
        # where min_c_w is the width of the narrower column
        self.max_column_span_part = max_column_span_part


DEFAULT_DETECTING_SETTINGS = TableDetectorSettings()


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
    def __init__(self,
                 cell: TableLocationCell,
                 pivot: str,
                 settings: TableDetectorSettings):
        self.cells: List[TableLocationCell] = [cell]
        self.pivot = pivot
        self.min = cell.get_coord(pivot)
        self.max = self.min
        self.settings = settings

    def __str__(self):
        return f'{len(self.cells)} cells'

    def __repr__(self):
        return self.__str__()

    @property
    def area(self) -> float:
        return sum([c.area for c in self.cells]) if self.cells else 0

    @property
    def bounding_rect(self) -> Optional[Tuple[float, float, float, float]]:
        if not self.cells:
            return None
        c = self.cells[0]
        x, y, r, b = c.x, c.y, c.x + c.w, c.y + c.h
        for i in range(1, len(self.cells)):
            c = self.cells[i]
            x = min(x, c.x)
            y = min(y, c.y)
            r = max(r, c.x + c.w)
            b = max(b, c.y + c.h)
        return x, y, r - x, b - y

    def add_cell_to_cluster(self, cell: TableLocationCell) -> bool:
        p = cell.get_coord(self.pivot)
        dist = min(abs(p - self.min), abs(p - self.max))
        if dist > self.settings.pivot_tolerance:
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
            if dist <= self.settings.pivot_tolerance:
                filtered.append(c)
        self.cells = filtered

    def remove_cell(self, c: TableLocationCell):
        try:
            self.cells.remove(c)
        except ValueError:
            pass

    def clusters_span(self, c: 'TableLocationCluster') -> bool:
        # do two columns (pivot != 'b') or two rows (pivot = 'b') span
        self_r = self.bounding_rect
        if not self_r:
            return False  # cluster is already "consumed" and its cells are deleted
        bound_r = c.bounding_rect
        if not bound_r:
            return False

        ax, ay, aw, ah = self_r
        bx, by, bw, bh = bound_r
        if self.pivot != 'b':  # check 2 columns
            min_size = min(aw, bw)
            span_part = self.get_span_part(ax, ax + aw, bx, bx + bw)
        else:  # check two rows
            min_size = min(ah, bh)
            span_part = self.get_span_part(ay, ay + ah, by, by + bh)
        return span_part > min_size * self.settings.max_column_span_part

    @classmethod
    def get_span_part(cls, al: float, ar: float, bl: float, br: float) -> float:
        # (al, ar) and (bl, br) are two spans
        # the function returns length of the a & b intersection
        if ar <= bl or br <= al:
            return 0
        if bl <= al and ar <= br:  # a is a part of b
            return ar - al
        if al <= bl and br <= ar:  # b is a part of a
            return br - bl
        if br >= ar >= bl:
            return ar - bl
        return br - al


class TableLocation:
    def __init__(self,
                 x: float,
                 y: float,
                 w: float,
                 h: float,
                 settings: TableDetectorSettings):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.settings = settings

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
                clusters.append(TableLocationCluster(cell, pivot, self.settings))

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

        # columns shouldn' intersect. If two columns intersects we remove the one with less cells
        self.consume_overlapping_clusters()

        col_cl = [
            self.clusters_by_pivot['l'],
            self.clusters_by_pivot['m'],
            self.clusters_by_pivot['r']
        ]
        col_cl.sort(key=lambda cl: sum([len(cluster.cells) for cluster in cl]), reverse=True)
        self.column_clusters = col_cl[0]

    def consume_overlapping_clusters(self):
        for key in ['l', 'm', 'r']:
            clusters = self.clusters_by_pivot[key]
            for i in range(len(clusters) - 1):
                a = clusters[i]
                if not a.cells:
                    continue
                for j in range(i + 1, len(clusters)):
                    b = clusters[j]
                    if not b.cells:
                        continue
                    if not a.clusters_span(b):
                        continue
                    # one clusters consumes another. We remove the smallest
                    if len(a.cells) < len(b.cells):
                        a.cells = []
                        break
                    else:
                        b.cells = []
            # remove consumed clusters (clusters without cells)
            self.clusters_by_pivot[key] = [c for c in clusters if c.cells]


class TableDetector:
    def __init__(self,
                 debug_image_path: str = '',
                 settings: TableDetectorSettings = DEFAULT_DETECTING_SETTINGS):
        self.settings = settings
        self.scale = 1.0
        self.gray_image = None
        self.cell_contours: List[TableLocationCell] = []
        self.page_blocks: List[TableLocation] = []
        self.debug_image_path = debug_image_path

    def find_tables(self, image_fn: str) -> List[TableLocation]:
        self.read_image(image_fn)
        self.detect_paragraphs()
        return self.detect_tables_in_blocks()

    def find_table_regions(self, image_fn: str) -> List[str]:
        # returns table regions in format that Camelot understands
        tables = self.find_tables(image_fn)
        im_ht = self.gray_image.shape[1]
        regions = [(t.x * self.scale, (im_ht - t.y) * self.scale,
                    (t.x + t.w) * self.scale, t.h * self.scale)
                   for t in tables]
        return [f'{round(x1)},{round(y1)},{round(x2)},{round(y2)}' for x1, y1, x2, y2 in regions]

    def read_image(self, image_fn: str):
        image = cv2.imread(image_fn)
        self.gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        max_dim = max(image.shape[0], image.shape[1])
        if max_dim > self.settings.max_image_dimension:
            self.scale = max_dim / self.settings.max_image_dimension
            w = round(image.shape[0] / self.scale)
            h = round(image.shape[1] / self.scale)
            self.gray_image = cv2.resize(self.gray_image, (w, h))

    def detect_paragraphs(self):
        blur_rad = self.settings.blur_radius_paragraph
        blur = cv2.GaussianBlur(self.gray_image, (blur_rad, blur_rad), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT,
                                           self.settings.cell_morph_shape_sz)

        # find cell contours
        dilate = cv2.dilate(thresh, kernel, iterations=self.settings.cell_dilate_iterations)
        cell_contours, _hr = cv2.findContours(dilate, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        self.build_cell_rects_from_contours(cell_contours)

        # find paragraph or table contours
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, self.settings.paragraph_morph_shape_sz)
        dilate = cv2.dilate(thresh, kernel, iterations=self.settings.paragraph_dilate_iterations)
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
            self.page_blocks.append(TableLocation(x, y, w, h, self.settings))

    def build_cell_rects_from_contours(self, cell_contours: List[Any]):
        selected = []
        for c in cell_contours:
            # c.shape[0] <= self.max_point_in_cell_contour
            bounding_rect = cv2.boundingRect(c)
            contour_area = cv2.contourArea(c)
            rect_area_sz = bounding_rect[2] * bounding_rect[3]
            if rect_area_sz < contour_area * self.settings.contour_square_area_share:
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
            if columns_count < self.settings.min_columns_in_table:
                continue

            # total area should be greater than k*block_area
            min_area = block.area * self.settings.cell_area_to_table_area
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