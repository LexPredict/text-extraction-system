from text_extraction_system.pdf.pdf import split_pdf_to_page_blocks
from shutil import copy

with split_pdf_to_page_blocks('/home/mikhail/lexpredict/misc/ocr_complicated1.pdf') as page_fns:
    for p in page_fns:
        copy(p, '/home/mikhail/lexpredict/misc/ocr_complicated1/')
