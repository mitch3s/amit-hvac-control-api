import unittest

from amit_hvac_control.api.utils import get_multipart_data


class GetMultipartDataTests(unittest.TestCase):
    def test_parts_have_no_content_type_header(self):
        mp = get_multipart_data({"key1": "value1", "key2": "value2"})

        for part, _encoding, _te_encoding in mp._parts:
            self.assertNotIn("Content-Type", part.headers)

    def test_parts_have_form_data_content_disposition(self):
        mp = get_multipart_data({"key1": "value1"})

        part, _encoding, _te_encoding = mp._parts[0]
        self.assertIn('name="key1"', part.headers["Content-Disposition"])
