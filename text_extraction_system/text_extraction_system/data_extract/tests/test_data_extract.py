import gc
import json
import pathlib
import tempfile

import cv2
import datetime
from typing import List

import msgpack
from PIL import Image

from text_extraction_system_api.dto import PlainTableOfContentsRecord, PlainTextPage

from text_extraction_system.commons.tests.commons import with_default_settings
from text_extraction_system.data_extract import data_extract
from text_extraction_system.data_extract.data_extract import process_pdf_page, get_sections_from_table_of_contents, \
    normalize_angle_90
from text_extraction_system.pdf.pdf import merge_pdf_pages, extract_page_ocr_images

base_dir_path = pathlib.Path(__file__).parent.resolve()
data_dir_path = base_dir_path / 'data'
tmp_results_path = pathlib.Path(tempfile.gettempdir()) / 'TES_tests'

# Create directory for temporary results
pathlib.Path(tmp_results_path).mkdir(parents=True, exist_ok=True)


@with_default_settings
def test_text_structure_extraction():
    fn = data_dir_path / 'structured_text.pdf'
    with data_extract.extract_text_and_structure(str(fn)) as (text, full_struct, _a, _b):
        struct = full_struct.text_structure
        assert 'idea if it is really' in text
        assert 'etect the sections' in text
        assert len(struct.pages) == 2
        assert len(struct.paragraphs) == 5
        assert len(struct.sentences) == 15

        # should be 2 sections but its a problem of lexnlp
        assert len(struct.sections) == 3


@with_default_settings
def test_different_languages_extraction_with_no_ocr():
    fn = data_dir_path / 'two_langs_no_ocr.pdf'
    with data_extract.extract_text_and_structure(str(fn), language="en_US") as (text, full_struct, _a, _b):
        struct = full_struct.text_structure
        assert 'This is top secret' in text
        assert len(struct.pages) == 1
        assert len(struct.paragraphs) == 1
        for i in struct.paragraphs:
            assert i.language == struct.language
        assert len(struct.sentences) == 2
        for i in struct.sentences:
            assert i.language == struct.language


@with_default_settings
def test_text_too_short():
    fn = data_dir_path / 'finstat90_rotation_set.pdf'
    with extract_page_ocr_images(str(fn), start_page=1, end_page=1) as image_fns:
        with process_pdf_page(image_fns[1]) as res:
            num_file_rotate = (1, res.ocred_page_fn, None)
            with merge_pdf_pages(str(fn), single_page_merge_num_file_rotate=num_file_rotate) as merged_pdf_fn:
                with data_extract.extract_text_and_structure(merged_pdf_fn, language="en_US") \
                        as (text, full_struct, _a, _b):
                    assert 'financial statements' in text.lower()


@with_default_settings
def test_get_sections_from_table_of_contents():
    toc_items: List[PlainTableOfContentsRecord] = [
        PlainTableOfContentsRecord(title='Heading 1', level=1, left=250, top=580, page=0),
        PlainTableOfContentsRecord(title='Heading 2', level=1, left=255, top=570, page=1),
        PlainTableOfContentsRecord(title='Heading 1.1', level=2, left=230, top=280, page=0),
        PlainTableOfContentsRecord(title='Heading 3', level=1, left=251, top=580, page=2)
    ]
    boxes = [
        [250, 580, 20, 40],
        [270, 580, 20, 40],
        [60, 540, 20, 40],
        [80, 540, 20, 40],
        # page 1
        [252, 578, 20, 40],
        [274, 578, 20, 40],
        [60, 540, 20, 40],
        [80, 536, 20, 40],
        # page 2
        [250, 580, 20, 40],
        [270, 580, 20, 40],
        [60, 540, 20, 40],
        [80, 540, 20, 40],
    ]
    pages: List[PlainTextPage] = [
        PlainTextPage(number=0, start=0, end=4, bbox=[0, 0, 440, 600], rotation=0),
        PlainTextPage(number=1, start=4, end=8, bbox=[0, 0, 440, 600], rotation=0),
        PlainTextPage(number=2, start=8, end=11, bbox=[0, 0, 440, 600], rotation=0)
    ]
    sections = get_sections_from_table_of_contents(toc_items, boxes, pages)
    assert len(sections) == len(toc_items)
    assert sections[1].title == 'Heading 1.1'
    assert sections[2].title == 'Heading 2'
    assert sections[0].start == 0
    assert sections[1].start == 3
    assert sections[2].start == 4


@with_default_settings
def test_rotate_image():
    """
    cs.transform(Matrix.getTranslateInstance(w/2, h/2));
    cs.transform(Matrix.getRotateInstance(Math.toRadians(contentsRotate), 0, 0));
    cs.transform(Matrix.getTranslateInstance(-w/2, -h/2));
    """
    src_path = data_dir_path / 'dummy_text.png'
    dst_path = tmp_results_path / 'dummy_text_r.png'

    angle = -5.8
    t1 = datetime.datetime.now()
    src = cv2.imread(str(src_path))
    h, w, _ = src.shape
    rotate_matrix = cv2.getRotationMatrix2D(center=(w/2, h/2), angle=angle, scale=1)
    if abs(round(angle/90)):
        h, w = w, h

    rotated_image = cv2.warpAffine(src=src, M=rotate_matrix, dsize=(w, h), borderValue=(255, 255, 255))
    try:
        cv2.imwrite(str(dst_path), rotated_image)
        assert (datetime.datetime.now() - t1).total_seconds() < 0.1
    finally:
        dst_path.unlink()


@with_default_settings
def test_speed():
    src_path = data_dir_path / 'dummy_text.png'
    dst_path = tmp_results_path / 'dummy_text_9.png'

    rot_angle = 9.0

    t1 = datetime.datetime.now()
    img = Image.open(src_path)
    img = img.convert('RGB')
    img = img.rotate(rot_angle, fillcolor=(255, 255, 255), expand=False)

    try:
        img.save(dst_path)
        assert (datetime.datetime.now() - t1).total_seconds() < 0.5
    finally:
        dst_path.unlink()


@with_default_settings
def test_normalize_angle_90():
    assert normalize_angle_90(-5.8) == -5.8
    assert normalize_angle_90(0.8) == 0.8
    assert round(normalize_angle_90(90.8), 1) == 0.8
    assert normalize_angle_90(88) == -2
    assert normalize_angle_90(-88) == 2
    assert normalize_angle_90(-92) == -2


@with_default_settings
def test_proto_memory_comparison():
    fn = data_dir_path / 'finstat90_rotation_set.pdf'
    with extract_page_ocr_images(str(fn), start_page=1, end_page=1) as image_fns:
        with process_pdf_page(image_fns[1]) as res:
            num_file_rotate = (1, res.ocred_page_fn, None)
            with merge_pdf_pages(str(fn), single_page_merge_num_file_rotate=num_file_rotate) as merged_pdf_fn:
                with data_extract.extract_text_and_structure(merged_pdf_fn, language="en_US") \
                        as (text, full_struct, _a, _b):
                    json_pdf_coords = json.dumps(full_struct.pdf_coordinates.to_dict(), indent=2)
                    json_text_structure = json.dumps(full_struct.text_structure.to_dict(), indent=2)
                    try:
                        gc.disable()
                        msgpack_pdf_coords = msgpack.packb(full_struct.pdf_coordinates.__dict__, use_bin_type=True,
                                                           use_single_float=True)
                        msgpack_text_struct = msgpack.packb(full_struct.text_structure.to_dict(), use_bin_type=True,
                                                            use_single_float=True)
                    finally:
                        gc.enable()

                    from google.protobuf.json_format import Parse
                    import text_extraction_system_api.python_pb2_files.contract_char_bboxes_pb2 as char_bboxes_pb2
                    import text_extraction_system_api.python_pb2_files.contract_pages_pb2 as pages_pb2

                    pdf_coords = full_struct.pdf_coordinates.to_dict()
                    pdf_coords["char_bboxes"] = [{'coords': item} for item in pdf_coords["char_bboxes"]]
                    proto_pdf_coords = Parse(json.dumps(pdf_coords), char_bboxes_pb2.CharBboxes()).SerializeToString()
                    proto_text_struct = Parse(json.dumps(full_struct.text_structure.to_dict()),
                                              pages_pb2.Pages()).SerializeToString()

                    assert len(str(json_pdf_coords)) > len(str(msgpack_pdf_coords)) > len(str(proto_pdf_coords))
                    assert len(str(json_text_structure)) > len(str(msgpack_text_struct)) > len(str(proto_text_struct))

                    # Simple structures do not big memory boost for protobuf
                    assert len(str(msgpack_pdf_coords)) / len(str(proto_pdf_coords)) < 1.5

                    # Large structures do better memory boost for protobuf
                    assert len(str(msgpack_text_struct)) / len(str(proto_text_struct)) > 1.5


@with_default_settings
def test_proto_speed_comparison():
    fn = data_dir_path / 'finstat90_rotation_set.pdf'
    iterate_amount = 1000

    with extract_page_ocr_images(str(fn), start_page=1, end_page=1) as image_fns:
        with process_pdf_page(image_fns[1]) as res:
            num_file_rotate = (1, res.ocred_page_fn, None)
            with merge_pdf_pages(str(fn), single_page_merge_num_file_rotate=num_file_rotate) as merged_pdf_fn:
                with data_extract.extract_text_and_structure(merged_pdf_fn, language="en_US") \
                        as (text, full_struct, _a, _b):
                    t1 = datetime.datetime.now()
                    for _ in range(iterate_amount):
                        json.dumps(full_struct.pdf_coordinates.to_dict(), indent=2)
                        json.dumps(full_struct.text_structure.to_dict(), indent=2)
                    json_execute_time = datetime.datetime.now() - t1
                    try:
                        gc.disable()
                        t1 = datetime.datetime.now()
                        for _ in range(iterate_amount):
                            msgpack.packb(full_struct.pdf_coordinates.__dict__, use_bin_type=True,
                                          use_single_float=True)
                            msgpack.packb(full_struct.text_structure.to_dict(), use_bin_type=True,
                                          use_single_float=True)
                        msgpack_execute_time = datetime.datetime.now() - t1
                    finally:
                        gc.enable()

                    from google.protobuf.json_format import Parse
                    import text_extraction_system_api.python_pb2_files.contract_char_bboxes_pb2 as char_bboxes_pb2
                    import text_extraction_system_api.python_pb2_files.contract_pages_pb2 as pages_pb2

                    t1 = datetime.datetime.now()
                    pdf_coords = full_struct.pdf_coordinates.to_dict()
                    pdf_coords["char_bboxes"] = [{'coords': item} for item in pdf_coords["char_bboxes"]]
                    for _ in range(iterate_amount):
                        Parse(json.dumps(pdf_coords), char_bboxes_pb2.CharBboxes()).SerializeToString()
                        Parse(json.dumps(full_struct.text_structure.to_dict()), pages_pb2.Pages()).SerializeToString()
                    proto_execute_time = datetime.datetime.now() - t1

                    assert json_execute_time.total_seconds() > proto_execute_time.total_seconds() \
                           > msgpack_execute_time.total_seconds()
                    # Protobuf is more than 2 times slower
                    assert proto_execute_time.total_seconds() / msgpack_execute_time.total_seconds() > 2
