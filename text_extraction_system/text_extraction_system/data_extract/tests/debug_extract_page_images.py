import os
import shutil

from text_extraction_system.pdf.pdf import split_pdf_to_page_blocks, extract_page_images
from text_extraction_system.commons.tests.commons import default_settings

fn = os.path.join(os.path.dirname(__file__), 'data', 'table-based-text_noocr.pdf')

with default_settings():
    with extract_page_images(fn) as pages:
        for pfn in pages:
            shutil.copy(pfn, str(os.path.join(os.path.dirname(__file__), 'data')) + '/')
