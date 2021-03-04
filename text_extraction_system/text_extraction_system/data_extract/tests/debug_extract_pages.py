import os
import shutil

from text_extraction_system.pdf.pdf import split_pdf_to_page_blocks
from text_extraction_system.pdf.convert_to_pdf import convert_to_pdf

fn = os.path.join(os.path.dirname(__file__), 'data', 'table-based-text.docx')

with convert_to_pdf(fn) as pdf_fn:
    with split_pdf_to_page_blocks(pdf_fn, 1) as pages:
        for pfn in pages:
            shutil.copy(pfn, '/home/mikhail/lexpredict/misc/20210304-2/')
