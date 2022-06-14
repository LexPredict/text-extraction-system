import os
import pathlib
import tempfile

from text_extraction_system_api.dto import TableParser

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract.camelot.camelot import extract_tables_from_pdf_file
from text_extraction_system.ocr.tables.table_detection import TableLocationCell, \
    TableLocationCluster, TableLocation, TableDetectorSettings
from text_extraction_system.ocr.tables.table_detection import DEFAULT_DETECTING_SETTINGS as DS

base_dir_path = pathlib.Path(__file__).parent.resolve()
data_dir_path = base_dir_path / 'data'
tmp_results_path = pathlib.Path(tempfile.gettempdir()) / 'TES_tests'

# Create directory for temporary results
pathlib.Path(tmp_results_path).mkdir(parents=True, exist_ok=True)


@with_default_settings
def test_corr_pdf():
    pdf_fn = data_dir_path / 'tables.pdf'
    extract_tables_from_pdf_file(str(pdf_fn), True, TableParser.area_stream, 60)


@with_default_settings
def test_table_cell_pivot():
    c = TableLocationCell(15, 100, 200, 20)
    assert c.get_coord('l') == 15
    assert c.get_coord('r') == 15 + 200
    assert c.get_coord('m') == 15 + 200 / 2
    assert c.get_coord('b') == 100 + 20
    assert c.area == 200 * 20


@with_default_settings
def test_cluster_area():
    c1 = TableLocationCell(15, 100, 200, 20)
    c2 = TableLocationCell(115, 100, 10, 20)
    c = TableLocationCluster(c1, 'l', DS)
    c.cells.append(c2)
    assert c.area == 200 * 20 + 10 * 20


@with_default_settings
def test_add_cell_to_cluster():
    c = TableLocationCluster(TableLocationCell(15, 100, 20, 20), 'l', DS)
    c.add_cell_to_cluster(TableLocationCell(18, 130, 10, 20))
    c.add_cell_to_cluster(TableLocationCell(21, 160, 10, 20))
    c.add_cell_to_cluster(TableLocationCell(24, 190, 200, 20))
    c.add_cell_to_cluster(TableLocationCell(31, 190, 10, 20))
    assert 4 == len(c.cells)

    c = TableLocationCluster(TableLocationCell(15, 100, 30, 20), 'm', DS)
    c.add_cell_to_cluster(TableLocationCell(18, 130, 30, 20))
    c.add_cell_to_cluster(TableLocationCell(21, 160, 30, 20))
    assert not c.add_cell_to_cluster(TableLocationCell(22, 160, 100, 20))
    c.add_cell_to_cluster(TableLocationCell(24, 190, 30, 20))
    assert c.add_cell_to_cluster(TableLocationCell(31, 190, 22, 20))
    assert 5 == len(c.cells)


@with_default_settings
def test_remove_distant_cells():
    c = TableLocationCluster(TableLocationCell(15, 100, 30, 20), 'm', DS)
    c.add_cell_to_cluster(TableLocationCell(18, 130, 30, 20))
    c.add_cell_to_cluster(TableLocationCell(21, 160, 30, 20))
    c.add_cell_to_cluster(TableLocationCell(22, 160, 100, 20))
    c.add_cell_to_cluster(TableLocationCell(24, 190, 30, 20))
    c.add_cell_to_cluster(TableLocationCell(31, 190, 22, 20))
    c.remove_distant_cells()
    assert 3 == len(c.cells)


@with_default_settings
def test_remove_distant_cells():
    cell = TableLocationCell(15, 100, 30, 20)
    c = TableLocationCluster(cell, 'm', DS)
    c.add_cell_to_cluster(TableLocationCell(18, 130, 30, 20))
    c.remove_cell(cell)
    c.remove_cell(cell)
    assert 1 == len(c.cells)


@with_default_settings
def test_bounding_rect():
    c = TableLocationCluster(TableLocationCell(15, 100, 30, 20), 'm', DS)
    c.add_cell_to_cluster(TableLocationCell(18, 130, 30, 20))
    c.add_cell_to_cluster(TableLocationCell(21, 160, 30, 20))
    assert c.bounding_rect == (15, 100, 21 + 30 - 15, 160 + 20 - 100)
    c.cells = []
    assert c.bounding_rect is None


@with_default_settings
def test_get_span_part():
    assert TableLocationCluster.get_span_part(10, 20, 30, 40) == 0
    assert TableLocationCluster.get_span_part(30, 40, 10, 20) == 0
    assert TableLocationCluster.get_span_part(10, 30, 25, 40) == 5
    assert TableLocationCluster.get_span_part(25, 40, 10, 30) == 5
    assert TableLocationCluster.get_span_part(25, 125, 25, 40) == 15
    assert TableLocationCluster.get_span_part(25, 40, 25, 125) == 15
    assert TableLocationCluster.get_span_part(25, 125, 45, 200) == 125 - 45
    assert TableLocationCluster.get_span_part(45, 200, 25, 125) == 125 - 45


@with_default_settings
def test_clusters_span():
    sets = TableDetectorSettings(max_column_span_part=0.3)
    a = TableLocationCluster(TableLocationCell(15, 100, 30, 20), 'm', sets)
    b = TableLocationCluster(TableLocationCell(30, 100, 30, 20), 'm', sets)
    assert a.clusters_span(b)  # 50% span
    sets.max_column_span_part = 0.6
    assert not a.clusters_span(b)


@with_default_settings
def test_get_clusters_border():
    a = TableLocationCluster(TableLocationCell(15, 100, 30, 20), 'm', DS)
    b = TableLocationCluster(TableLocationCell(30, 100, 30, 20), 'm', DS)
    assert a.get_clusters_border(b) == -1
    a.cells[0].y = 150
    assert a.get_clusters_border(b) == (150 + 100 + 20) / 2


@with_default_settings
def test_consume_overlapping_clusters():
    sets = TableDetectorSettings(max_column_span_part=0.3)
    a = TableLocationCluster(TableLocationCell(15, 100, 35, 20), 'm', sets)
    a.add_cell_to_cluster(TableLocationCell(18, 120, 32, 20))
    b = TableLocationCluster(TableLocationCell(45, 150, 35, 20), 'm', sets)

    tl = TableLocation(0, 0, 300, 300, sets)
    tl.clusters_by_pivot['l'] = [a, b]
    tl.consume_overlapping_clusters()
    # clusters shouldn't have been changed
    assert len(tl.clusters_by_pivot['l']) == 2

    b.cells[0].x = 22
    tl.consume_overlapping_clusters()
    # cluster b should be consumed
    assert len(tl.clusters_by_pivot['l']) == 1
    assert len(tl.clusters_by_pivot['l'][0].cells) == 2


@with_default_settings
def test_table_loc_area():
    tl = TableLocation(1, 100, 20, 300, DS)
    assert 20 * 300 == tl.area


@with_default_settings
def test_point_inside():
    tl = TableLocation(1, 100, 20, 300, DS)
    assert tl.point_inside(2, 101)
    assert not tl.point_inside(22, 101)


@with_default_settings
def test_cell_inside():
    tl = TableLocation(1, 100, 20, 300, DS)
    assert tl.cell_inside(TableLocationCell(15, 101, 4, 20))
    assert not tl.cell_inside(TableLocationCell(15, 101, 30, 20))


@with_default_settings
def test_try_add_cell():
    tl = TableLocation(1, 100, 100, 300, DS)
    assert tl.try_add_cell(TableLocationCell(15, 101, 14, 20))
    assert tl.try_add_cell(TableLocationCell(18, 121, 14, 20))
    assert tl.try_add_cell(TableLocationCell(17, 131, 14, 20))
    assert tl.try_add_cell(TableLocationCell(31, 102, 14, 20))
    assert not tl.try_add_cell(TableLocationCell(15, 101, 230, 20))
    assert not tl.try_add_cell(TableLocationCell(15, 101, 20, 320))

    assert 2 == len(tl.clusters_by_pivot['l'])
    assert 2 == len(tl.clusters_by_pivot['m'])
    assert 2 == len(tl.clusters_by_pivot['r'])


# ToDo: fix TableDetector bugs and uncomment this test
# @with_default_settings
# def test_clear_clusters():
#     tl = TableLocation(1, 100, 100, 300, DS)
#     tl.try_add_cell(TableLocationCell(15, 101, 14, 20))
#     tl.try_add_cell(TableLocationCell(18, 121, 14, 20))
#     tl.try_add_cell(TableLocationCell(17, 131, 31, 20))
#     tl.try_add_cell(TableLocationCell(21, 139, 14, 20))
#     tl.try_add_cell(TableLocationCell(23, 141, 14, 20))
#     tl.try_add_cell(TableLocationCell(25, 151, 14, 20))
#     tl.try_add_cell(TableLocationCell(38, 102, 14, 20))
#     tl.try_add_cell(TableLocationCell(39, 102, 14, 20))
#
#     assert 2 == len(tl.clusters_by_pivot['l'])
#     assert 6 == len(tl.clusters_by_pivot['l'][0].cells)
#     assert 2 == len(tl.clusters_by_pivot['l'][1].cells)
#     assert 3 == len(tl.clusters_by_pivot['m'])
#     assert 5 == len(tl.clusters_by_pivot['m'][0].cells)
#     assert 1 == len(tl.clusters_by_pivot['m'][1].cells)
#     assert 2 == len(tl.clusters_by_pivot['m'][2].cells)
#     assert 2 == len(tl.clusters_by_pivot['r'])
#     assert 5 == len(tl.clusters_by_pivot['r'][0].cells)
#     assert 3 == len(tl.clusters_by_pivot['r'][1].cells)
#
#     tl.clear_clusters()
#
#     assert 2 == len(tl.column_clusters)
#     assert 5 == len(tl.column_clusters[0].cells)


@with_default_settings
def debug_mixed_tables():
    fn = ''  # page image file path without dot and extension
    from text_extraction_system.ocr.tables.table_detection import TableDetector
    sets = TableDetectorSettings()
    TableDetector(fn, sets).find_tables(fn + '.png')
