from text_extraction_system.ocr.ocr import ocr_page_to_pdf
from text_extraction_system.pdf.pdf import merge_pdf_pages, log
import shutil
from text_extraction_system.commons.tests.commons import default_settings
from logging import DEBUG

with default_settings():
    log.setLevel(DEBUG)
    with ocr_page_to_pdf('/home/mikhail/lexpredict/misc/ocr_complicated1/page_no_text_00034.png',
                         glyphless_text_only=True) as fn:
        with merge_pdf_pages('/home/mikhail/lexpredict/misc/ocr_complicated1/ocr_complicated1_0034.pdf',
                             single_page_merge_num_file=(1, fn)) as fn1:
            shutil.copy(fn1, '/home/mikhail/lexpredict/misc/ocr_complicated1/ocred/')
