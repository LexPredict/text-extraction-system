import os

from text_extraction_system.data_extract import plain_text

data_dir = os.path.join(os.path.dirname(__file__), 'data')


def test_text_structure_extraction():
    fn = os.path.join(data_dir, 'structured_text.pdf')
    text, struct = plain_text.extract_text_and_structure(fn)
    assert 'idea if it is really' in text
    assert 'etect the sections' in text
    assert len(struct.pages) == 2
    assert len(struct.paragraphs) == 6
    assert len(struct.sentences) == 15

    # should be 2 sections but its a problem of lexnlp
    assert len(struct.sections) == 3
