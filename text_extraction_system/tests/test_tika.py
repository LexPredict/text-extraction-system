import os

from text_extraction_system.tika import tika_extract_xhtml

data_dir = os.path.join(os.path.dirname(__file__), 'data')


def test_tika1():
    fn = os.path.join(data_dir, 'pdf_9_pages.pdf')
    text: str = tika_extract_xhtml(fn)
    with open('/home/mikhail/tika1111111/output.xhtml', 'w') as f:
        f.write(text)
    assert len(text) > 0
