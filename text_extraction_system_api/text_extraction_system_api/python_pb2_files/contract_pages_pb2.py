# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: contract_pages.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import wrappers_pb2 as google_dot_protobuf_dot_wrappers__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x14\x63ontract_pages.proto\x1a\x1egoogle/protobuf/wrappers.proto\"_\n\x04Page\x12\x11\n\x06number\x18\x01 \x02(\x05:\x01\x30\x12\x10\n\x05start\x18\x02 \x02(\x05:\x01\x30\x12\x0e\n\x03\x65nd\x18\x03 \x02(\x05:\x01\x30\x12\x10\n\x08rotation\x18\x04 \x01(\x02\x12\x10\n\x04\x62\x62ox\x18\x05 \x03(\x02\x42\x02\x10\x01\"V\n\x08Sentence\x12\r\n\x05start\x18\x01 \x01(\x05\x12\x0b\n\x03\x65nd\x18\x02 \x01(\x05\x12.\n\x08language\x18\x03 \x01(\x0b\x32\x1c.google.protobuf.StringValue\"W\n\tParagraph\x12\r\n\x05start\x18\x01 \x01(\x05\x12\x0b\n\x03\x65nd\x18\x02 \x01(\x05\x12.\n\x08language\x18\x03 \x01(\x0b\x32\x1c.google.protobuf.StringValue\"\xc5\x01\n\x07Section\x12\r\n\x05start\x18\x01 \x01(\x05\x12\x0b\n\x03\x65nd\x18\x02 \x01(\x05\x12+\n\x05title\x18\x03 \x01(\x0b\x32\x1c.google.protobuf.StringValue\x12\x13\n\x0btitle_start\x18\x04 \x01(\x05\x12\x11\n\ttitle_end\x18\x05 \x01(\x05\x12\r\n\x05level\x18\x06 \x01(\x05\x12\x11\n\tabs_level\x18\x07 \x01(\x05\x12\x0c\n\x04left\x18\x08 \x01(\x02\x12\x0b\n\x03top\x18\t \x01(\x02\x12\x0c\n\x04page\x18\n \x01(\x05\"u\n\x0eTableOfContent\x12+\n\x05title\x18\x01 \x01(\x0b\x32\x1c.google.protobuf.StringValue\x12\r\n\x05level\x18\x02 \x01(\x05\x12\x0c\n\x04left\x18\x03 \x01(\x05\x12\x0b\n\x03top\x18\x04 \x01(\x05\x12\x0c\n\x04page\x18\x05 \x01(\x05\"\x80\x02\n\x05Pages\x12+\n\x05title\x18\x01 \x01(\x0b\x32\x1c.google.protobuf.StringValue\x12.\n\x08language\x18\x02 \x01(\x0b\x32\x1c.google.protobuf.StringValue\x12\x14\n\x05pages\x18\x03 \x03(\x0b\x32\x05.Page\x12\x1c\n\tsentences\x18\x04 \x03(\x0b\x32\t.Sentence\x12\x1e\n\nparagraphs\x18\x05 \x03(\x0b\x32\n.Paragraph\x12\x1a\n\x08sections\x18\x06 \x03(\x0b\x32\x08.Section\x12*\n\x11table_of_contents\x18\x07 \x03(\x0b\x32\x0f.TableOfContent')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'contract_pages_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _PAGE.fields_by_name['bbox']._options = None
  _PAGE.fields_by_name['bbox']._serialized_options = b'\020\001'
  _PAGE._serialized_start=56
  _PAGE._serialized_end=151
  _SENTENCE._serialized_start=153
  _SENTENCE._serialized_end=239
  _PARAGRAPH._serialized_start=241
  _PARAGRAPH._serialized_end=328
  _SECTION._serialized_start=331
  _SECTION._serialized_end=528
  _TABLEOFCONTENT._serialized_start=530
  _TABLEOFCONTENT._serialized_end=647
  _PAGES._serialized_start=650
  _PAGES._serialized_end=906
# @@protoc_insertion_point(module_scope)
