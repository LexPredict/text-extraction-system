from typing import List

from camelot.core import Table as CamelotTable
from camelot.parsers.lattice import Lattice
from camelot.utils import get_text_objects
from pdfminer.layout import LTPage
import os


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


def extract_tables(pageno: int,
                   page_layout: LTPage,
                   pdf_page_image_fn: str) -> List[CamelotTable]:
    lattice: CustomizedLattice = CustomizedLattice()
    lattice.imagename = pdf_page_image_fn
    lattice.layout = page_layout
    width = page_layout.bbox[2]
    height = page_layout.bbox[3]
    dim = (width, height)
    lattice.dimensions = dim
    # putting a dummy file name to avoid Camelot arguing
    # Camelot extracts the page number from the file name.
    return lattice.extract_tables(f'page-{pageno}.pdf')
