import shutil

from text_extraction_system.pdf.pdf import split_pdf_to_page_blocks

pdf_fn = '/home/mikhail/lexpredict/misc/angles/wrong_angle6.pdf'
with split_pdf_to_page_blocks(pdf_fn, 1) as pages:
    shutil.copy(pages[96], '/home/mikhail/lexpredict/misc/angles/20210504/')
