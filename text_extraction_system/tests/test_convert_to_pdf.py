import os

from text_extraction_system.convert_to_pdf import convert_to_pdf


def test_basic_conversion():
    with convert_to_pdf(__file__) as pdf_temp_file:
        assert os.path.getsize(pdf_temp_file) > 100
        with open(pdf_temp_file, 'rb') as f:
            pdf_contents = f.read()
            # print(pdf_contents)
            assert b'%PDF' in pdf_contents and b'%%EOF' in pdf_contents
    assert not os.path.exists(pdf_temp_file)
    assert not os.path.exists(os.path.dirname(pdf_temp_file))
