import os

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.ocr.tables.table_detection import TableLocationCell, TableLocationCluster, TableLocation

data_dir = os.path.join(os.path.dirname(__file__), 'data')


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
    c = TableLocationCluster(c1, 'l')
    c.cells.append(c2)
    assert c.area == 200 * 20 + 10 * 20


@with_default_settings
def test_add_cell_to_cluster():
    c = TableLocationCluster(TableLocationCell(15, 100, 20, 20), 'l')
    c.add_cell_to_cluster(TableLocationCell(18, 130, 10, 20))
    c.add_cell_to_cluster(TableLocationCell(21, 160, 10, 20))
    c.add_cell_to_cluster(TableLocationCell(24, 190, 200, 20))
    c.add_cell_to_cluster(TableLocationCell(31, 190, 10, 20))
    assert 4 == len(c.cells)

    c = TableLocationCluster(TableLocationCell(15, 100, 30, 20), 'm')
    c.add_cell_to_cluster(TableLocationCell(18, 130, 30, 20))
    c.add_cell_to_cluster(TableLocationCell(21, 160, 30, 20))
    assert not c.add_cell_to_cluster(TableLocationCell(22, 160, 100, 20))
    c.add_cell_to_cluster(TableLocationCell(24, 190, 30, 20))
    assert c.add_cell_to_cluster(TableLocationCell(31, 190, 22, 20))
    assert 5 == len(c.cells)


@with_default_settings
def test_remove_distant_cells():
    c = TableLocationCluster(TableLocationCell(15, 100, 30, 20), 'm')
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
    c = TableLocationCluster(cell, 'm')
    c.add_cell_to_cluster(TableLocationCell(18, 130, 30, 20))
    c.remove_cell(cell)
    c.remove_cell(cell)
    assert 1 == len(c.cells)


@with_default_settings
def test_table_loc_area():
    l = TableLocation(1, 100, 20, 300)
    assert 20 * 300 == l.area


@with_default_settings
def test_point_inside():
    l = TableLocation(1, 100, 20, 300)
    assert l.point_inside(2, 101)
    assert not l.point_inside(22, 101)


@with_default_settings
def test_cell_inside():
    l = TableLocation(1, 100, 20, 300)
    assert l.cell_inside(TableLocationCell(15, 101, 4, 20))
    assert not l.cell_inside(TableLocationCell(15, 101, 30, 20))


@with_default_settings
def test_try_add_cell():
    l = TableLocation(1, 100, 100, 300)
    assert l.try_add_cell(TableLocationCell(15, 101, 14, 20))
    assert l.try_add_cell(TableLocationCell(18, 121, 14, 20))
    assert l.try_add_cell(TableLocationCell(17, 131, 14, 20))
    assert l.try_add_cell(TableLocationCell(31, 102, 14, 20))
    assert not l.try_add_cell(TableLocationCell(15, 101, 230, 20))
    assert 2 == len(l.clusters_by_pivot['l'])
    assert 3 == len(l.clusters_by_pivot['b'])


@with_default_settings
def test_clear_clusters():
    l = TableLocation(1, 100, 100, 300)
    l.try_add_cell(TableLocationCell(15, 101, 14, 20))
    l.try_add_cell(TableLocationCell(18, 121, 14, 20))
    l.try_add_cell(TableLocationCell(17, 131, 31, 20))
    l.try_add_cell(TableLocationCell(21, 139, 14, 20))
    l.try_add_cell(TableLocationCell(23, 141, 14, 20))
    l.try_add_cell(TableLocationCell(25, 151, 14, 20))
    l.try_add_cell(TableLocationCell(38, 102, 14, 20))
    l.try_add_cell(TableLocationCell(39, 102, 14, 20))
    assert 2 == len(l.clusters_by_pivot['l'])
    assert 6 == len(l.clusters_by_pivot['l'][0].cells)
    assert 2 == len(l.clusters_by_pivot['l'][1].cells)

    l.clear_clusters()
    assert 2 == len(l.column_clusters)
    assert 5 == len(l.column_clusters[0].cells)


@with_default_settings
def debug_mixed_tables():
    fn = ''  # page image file path without dot and extension
    from text_extraction_system.ocr.tables.table_detection import TableDetector
    TableDetector(fn).find_tables(fn + '.png')
