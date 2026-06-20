import unittest

from bs4 import BeautifulSoup

from amit_hvac_control.api.parsing import (
    UnexpectedResponseException,
    require_class,
    require_match,
    require_selector,
)
from amit_hvac_control.api.status import StatusApi
from amit_hvac_control.api.temperature import TemperatureApi
from amit_hvac_control.api.ventilation import VentilationApi


class ParsingErrorTests(unittest.TestCase):
    def test_require_class_reports_missing_field(self):
        soup = BeautifulSoup("<html></html>", "html.parser")

        with self.assertRaisesRegex(
            UnexpectedResponseException, "Missing room temperature"
        ):
            require_class(soup, "AWNumericView1", "room temperature")

    def test_require_selector_reports_missing_field(self):
        soup = BeautifulSoup("<html></html>", "html.parser")

        with self.assertRaisesRegex(UnexpectedResponseException, "Missing CO2 value"):
            require_selector(soup, ".AWNumericView2", "CO2 value")

    def test_require_match_reports_missing_field(self):
        with self.assertRaisesRegex(UnexpectedResponseException, "Missing heating mode"):
            require_match(r"AWSCaseImage1v=(\d)", "", "heating mode")

    def test_status_missing_room_temperature_raises_parse_error(self):
        api = StatusApi(session=None)
        html = """
            <span class="AWNumericView2">500</span>
            <span class="AWNumericView3">21.0</span>
            <script>AWSCaseLabel1v=1;AWSCaseLabel2v=2;AWSCaseLabel3v=0;</script>
        """

        with self.assertRaisesRegex(
            UnexpectedResponseException, "Missing room temperature"
        ):
            api._extract_overview_details(html)

    def test_temperature_missing_heating_mode_raises_parse_error(self):
        api = TemperatureApi(session=None)
        html = b"""
            <span class="AWNumericView1">21.5</span>
            <span class="AWNumericView2">22.0</span>
        """

        with self.assertRaisesRegex(UnexpectedResponseException, "Missing heating mode"):
            api._extract_temperature_data(html)

    def test_ventilation_missing_heating_level_raises_parse_error(self):
        api = VentilationApi(session=None)
        html = b"""
            <span class="AWNumericView1">600</span>
            <span class="AWNumericView2">20.0</span>
            <input class="AWNumericEditButton1" value="22.0">
            <input class="AWNumericEditButton2" value="700">
            <script>AWSCaseLabel1v=2;</script>
        """

        with self.assertRaisesRegex(UnexpectedResponseException, "Missing heating level"):
            api._extract_data(html)


if __name__ == "__main__":
    unittest.main()
