import os

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract import data_extract

data_dir = os.path.join(os.path.dirname(__file__), 'data')


@with_default_settings
def test_text_structure_extraction():
    fn = os.path.join(data_dir, 'structured_text.pdf')
    text, struct = data_extract.extract_text_and_structure_from_file(fn)
    assert 'idea if it is really' in text
    assert 'etect the sections' in text
    assert len(struct.pages) == 2
    assert len(struct.paragraphs) == 6
    assert len(struct.sentences) == 15

    # should be 2 sections but its a problem of lexnlp
    assert len(struct.sections) == 3


@with_default_settings
def test_text_structure_extraction():
    from text_extraction_system.commons.sysutils import increase_recursion_limit
    # without the increasing the recursion limit pdfminer
    # crashes on some of the structures of this document
    increase_recursion_limit()
    fn = os.path.join(data_dir, 'recursion1.pdf')
    text, struct = data_extract.extract_text_and_structure_from_file(fn)
    assert len(struct.pages) > 2
