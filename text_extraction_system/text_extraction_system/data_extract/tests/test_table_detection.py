import os

from text_extraction_system.commons.tests.commons import with_default_settings

data_dir = os.path.join(os.path.dirname(__file__), 'data')


@with_default_settings
def test_mixed_tables():
    fn = '/home/andrey/Pictures/skewed_borderless.png'
    from text_extraction_system.ocr.tables.table_detection import TableDetector
    TableDetector().find_tables(fn)


@with_default_settings
def test_mixed_tables_2():
    fn = '/home/andrey/Pictures/no_tables.png'
    from text_extraction_system.ocr.tables.table_detection import TableDetector
    TableDetector().find_tables(fn)
