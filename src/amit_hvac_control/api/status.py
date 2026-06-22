from __future__ import annotations
import re
from aiohttp import ClientSession
from bs4 import BeautifulSoup

from amit_hvac_control.api.parsing import require_class, require_selector
from amit_hvac_control.models import HeatingMode, Season, VentilationMode

MAIN_URL = "/pages/index.hta"


class DataResult:
    def __init__(
        self,
        temperature: float,
        air_temperature: float,
        co_2: int,
        ventilation_mode: VentilationMode,
        season: Season,
        heating_mode: HeatingMode,
    ):
        self.temperature = temperature
        self.air_temperature = air_temperature
        self.co_2 = co_2
        self.ventilation_mode = ventilation_mode
        self.season = season
        self.heating_mode = heating_mode

    def __str__(self):
        return f"""
Air temperature:    {self.temperature}
Room temperature:   {self.air_temperature}
CO2:                {self.co_2}
Ventilation:    {self.ventilation_mode.name}
Comfort mode:   {self.heating_mode.name}
Season:         {self.season.name}
"""


class StatusApi:
    """Status API."""

    def __init__(self, session: ClientSession):
        self.session = session

    async def async_get_overview(self) -> DataResult:
        async with self.session.get(MAIN_URL) as response:
            text = await response.text()
            return self._extract_overview_details(text)

    def _extract_overview_details(self, content: str):
        soup = BeautifulSoup(content, "html.parser")

        room_temp_el = require_class(soup, "AWNumericView1", "room temperature")
        air_room_temp_el = require_class(soup, "AWNumericView3", "air temperature")
        co2_el = require_selector(
            soup, ".AWNumericView2,.AWNumericView2-alert-max", "CO2 value"
        )

        labels = self._get_aws_case_labels(content)

        temp_val = float(room_temp_el.text)
        air_temp_val = float(air_room_temp_el.text)
        co2_val = int(co2_el.text)

        return DataResult(
            temperature=temp_val,
            air_temperature=air_temp_val,
            co_2=co2_val,
            ventilation_mode=labels["ventilation"],
            season=labels["season"],
            heating_mode=labels["heating"],
        )

    def _get_aws_case_labels(self, contents: str):
        statuses = {}

        matches = re.findall(r"AWSCaseLabel(\d)v=(\d)", contents)
        for key, value in matches:
            value_number = int(value)
            match key:
                case "1":
                    statuses["season"] = Season(value_number)
                case "2":
                    statuses["ventilation"] = VentilationMode(value_number)
                case "3":
                    statuses["heating"] = HeatingMode(value_number)

        return statuses
