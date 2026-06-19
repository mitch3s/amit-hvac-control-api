import unittest

from amit_hvac_control.api.ventilation import VentilationApi
from amit_hvac_control.models import VentilationMode


class VentilationBitFieldTests(unittest.TestCase):
    def test_missing_bit_fields_default_to_off(self):
        result = VentilationApi(None)._get_bit_fields("")

        self.assertFalse(result.heating_on)
        self.assertEqual(result.ventilation_speed, VentilationMode.OFF)

    def test_missing_speed_bits_are_treated_as_false(self):
        contents = "AWSCaseLabelBit1_foo(1&1)\nAWSCaseLabelBit3_foo(1&1)"

        result = VentilationApi(None)._get_bit_fields(contents)

        self.assertTrue(result.heating_on)
        self.assertEqual(result.ventilation_speed, VentilationMode.MEDIUM)
