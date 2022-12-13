import os
from typing import List

from camelot.core import Table as CamelotTable
from camelot.parsers.lattice import Lattice
from camelot.parsers.stream import Stream
from camelot.utils import get_text_objects
from pdfminer.layout import LTPage
from text_extraction_system_api.dto import TableParser

from text_extraction_system.ocr.tables.table_detection import TableDetector
from text_extraction_system.pdf.pdf import iterate_pages, extract_page_images_from_pdf


class CustomizedLattice(Lattice):

    def _generate_image(self):
        # We don't need to additionally generate the image here as it is already generated
        # for the OCR needs.
        # self.imagename should be assigned already.
        pass

    def _generate_layout(self, filename, layout_kwargs):
        # Copied from camelot/parsers/base/BaseParser._generate_layout()
        # with removing the actual layout generation because we already
        # have the layout for other needs.

        self.filename = filename
        self.layout_kwargs = layout_kwargs

        # self.layout, self.dimensions = get_page_layout(filename, **layout_kwargs)

        self.images = get_text_objects(self.layout, ltype="image")
        self.horizontal_text = get_text_objects(self.layout, ltype="horizontal_text")
        self.vertical_text = get_text_objects(self.layout, ltype="vertical_text")
        self.pdf_width, self.pdf_height = self.dimensions
        self.rootname, __ = os.path.splitext(self.filename)


class CustomizedStream(Stream):

    def _generate_layout(self, filename, layout_kwargs):
        # Copied from camelot/parsers/base/BaseParser._generate_layout() with removing the actual layout generation
        # because we already have the layout for other needs.
        self.filename = filename
        self.layout_kwargs = layout_kwargs
        # self.layout, self.dimensions = get_page_layout(filename, **layout_kwargs)
        self.images = get_text_objects(self.layout, ltype="image")
        self.horizontal_text = get_text_objects(self.layout, ltype="horizontal_text")
        self.vertical_text = get_text_objects(self.layout, ltype="vertical_text")
        self.pdf_width, self.pdf_height = self.dimensions
        self.rootname, __ = os.path.splitext(self.filename)


def extract_tables(pageno: int,
                   page_layout: LTPage,
                   pdf_page_image_fn: str,
                   table_parser: TableParser = TableParser.lattice,
                   min_accuracy: int = 60) -> List[CamelotTable]:
    extractor = get_extractor(pdf_page_image_fn, table_parser)
    if not extractor:
        return []
    extractor.imagename = pdf_page_image_fn
    extractor.layout = page_layout
    width = page_layout.bbox[2]
    height = page_layout.bbox[3]
    dim = (width, height)
    extractor.dimensions = dim
    # putting a dummy file name to avoid Camelot arguing. Camelot extracts the page number from the file name.
    try:
        tables = extractor.extract_tables(f'page-{pageno}.pdf', suppress_stdout=True)
    except Exception:
        tables = []
    return [t for t in tables if t.accuracy >= min_accuracy]


def get_extractor(pdf_page_image_fn: str,
                  table_parser: TableParser = TableParser.lattice):
    areas = None
    detect_areas = table_parser == TableParser.area_stream or table_parser == TableParser.area_lattice
    extract_method = 'lattice' if table_parser == TableParser.lattice or table_parser == TableParser.area_lattice \
        else 'stream'
    if detect_areas:
        detector = TableDetector()
        areas = detector.find_table_regions(pdf_page_image_fn)
        if not areas:
            return
    extractor = CustomizedLattice(table_regions=areas) if extract_method == 'lattice' \
        else CustomizedStream(split_text=False, edge_tol=1500, table_regions=areas)
    return extractor


def extract_tables_from_pdf_file(pdf_fn: str,
                                 pdfminer_advanced_detection: bool = False,
                                 table_parser: TableParser = TableParser.lattice,
                                 min_accuracy: int = 60) -> List[CamelotTable]:
    res: List[CamelotTable] = list()
    with extract_page_images_from_pdf(pdf_fn, dpi=71) as image_fns:
        page_num = 0
        for ltpage in iterate_pages(pdf_fn, use_advanced_detection=pdfminer_advanced_detection):
            if page_num + 1 not in image_fns:
                continue
            page_image_fn = image_fns[page_num+1]
            camelot_tables: List[CamelotTable] = extract_tables(
                page_num, ltpage, page_image_fn, table_parser, min_accuracy)
            if camelot_tables:
                res += camelot_tables
            page_num += 1
    return res or None


def extract_tables_from_pdf_file_stream(pdf_fn: str, pdfminer_advanced_detection: bool = False) -> List[CamelotTable]:
    res: List[CamelotTable] = list()
    page_num = 0
    for ltpage in iterate_pages(pdf_fn, use_advanced_detection=pdfminer_advanced_detection):
        camelot_tables: List[CamelotTable] = extract_tables_borderless(page_num, ltpage)
        if camelot_tables:
            res += camelot_tables
        page_num += 1
    return res or None


def extract_tables_borderless(pageno: int, page_layout: LTPage) -> List[CamelotTable]:
    stream: CustomizedStream = CustomizedStream(row_tol=500)
    stream.layout = page_layout
    width = page_layout.bbox[2]
    height = page_layout.bbox[3]
    dim = (width, height)
    stream.dimensions = dim
    # putting a dummy file name to avoid Camelot arguing
    # Camelot extracts the page number from the file name.
    return stream.extract_tables(f'page-{pageno}.pdf', suppress_stdout=True)
