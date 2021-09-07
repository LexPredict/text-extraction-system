"""
    Copyright (C) 2017, ContraxSuite, LLC

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    You can also be released from the requirements of the license by purchasing
    a commercial license from ContraxSuite, LLC. Buying such a license is
    mandatory as soon as you develop commercial activities involving ContraxSuite
    software without disclosing the source code of your own applications.  These
    activities include: offering paid services to customers as an ASP or "cloud"
    provider, processing documents on the fly in a web application,
    or shipping ContraxSuite within a closed source product.
"""
from unittest import TestCase

# -*- coding: utf-8 -*-


__author__ = "ContraxSuite, LLC; LexPredict, LLC"
__copyright__ = "Copyright 2015-2021, ContraxSuite, LLC"
__license__ = "https://github.com/LexPredict/lexpredict-contraxsuite/blob/2.0.0/LICENSE"
__version__ = "2.0.0"
__maintainer__ = "LexPredict, LLC"
__email__ = "support@contraxsuite.com"

from text_extraction_system_api.pdf_coordinates.pdf_coords_common import find_page_by_smb_index


class TestCoordsLocation(TestCase):

    def test_get_index_by_coords(self):
        pages = [(0, 1192), (1192, 2900), (2900, 5819)]
        self.assertEqual(0, find_page_by_smb_index(pages, 0))
        self.assertEqual(0, find_page_by_smb_index(pages, 1))
        self.assertEqual(1, find_page_by_smb_index(pages, 1192))
        self.assertEqual(1, find_page_by_smb_index(pages, 1700))
        self.assertEqual(-1, find_page_by_smb_index(pages, 5819))

        pages = [(i * 100, i * 100 + 100) for i in range(40)]
        self.assertEqual(0, find_page_by_smb_index(pages, 0))
        self.assertEqual(0, find_page_by_smb_index(pages, 10))
        self.assertEqual(-1, find_page_by_smb_index(pages, pages[-1][1]))
        self.assertEqual(3, find_page_by_smb_index(pages, 300))
        self.assertEqual(3, find_page_by_smb_index(pages, 399))
        self.assertEqual(4, find_page_by_smb_index(pages, 400))

