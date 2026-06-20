from aiohttp import ClientSession
from bs4 import BeautifulSoup

from amit_hvac_control.api.parsing import require_class, require_match
from amit_hvac_control.api.utils import get_multipart_data
from amit_hvac_control.models import HeatingMode, Season

HEATING_URL = "/pages/page00/Vytapeni.hta"


class TemperatureResult:
    def __init__(self, temp_actual: float, temp_set: float, heating_mode: HeatingMode):
        self.actual_temperature = temp_actual
        self.set_temperature = temp_set
        self.heating_mode = heating_mode

    def __str__(self):
        return f"""
Actual: {self.actual_temperature}
Set: {self.set_temperature}
Heating mode: {self.heating_mode.name}
"""


class TemperatureApi:
    """Temperature API."""

    def __init__(self, session: ClientSession):
        self.session = session

    async def async_get_data(self):
        async with self.session.get(HEATING_URL) as response:
            content = await response.read()
            return self._extract_temperature_data(content)

    async def async_set_minimal_temperature(self, temp_val: float):
        post_data = {
            "NUMEDIT_i1w4102s255t2j1k1g7a15.00m30.00": temp_val,
            "BTNSUB_g7": "",
        }
        return await self._async_save(post_data)

    def async_set_temperature(self, temp_val: float):
        post_data = {
            "NUMEDIT_i1w4101s255t2j1k1g6a15.00m30.00": temp_val,
            "BTNSUB_g6": "",
        }
        return self._async_save(post_data)

    def async_set_season(self, season: Season):
        save_val = season.get_save_value()
        post_data = {**save_val}
        return self._async_save(post_data)

    def async_set_heading_mode(self, heating_mode: HeatingMode):
        save_val = heating_mode.get_button()
        post_data = {
            save_val: "",
            "SET_i1w4073s255t32j1k1g3": 2,
            "SET_i1w4073s255t32j1k1g4": 1,
            "SET_i1w4073s255t32j1k1g5": 0,
        }
        return self._async_save(post_data)

    async def _async_save(self, post: dict):
        data = get_multipart_data(post)
        
        async with self.session.post(HEATING_URL, data=data) as result:
            return result.ok

    def _extract_temperature_data(self, content: bytes):
        soup = BeautifulSoup(content, "html.parser")

        temp_act_el = require_class(soup, "AWNumericView1", "actual temperature")
        temp_set_el = require_class(soup, "AWNumericView2", "set temperature")

        temp_act = float(temp_act_el.text)
        temp_set = float(temp_set_el.text)

        html = str(soup)
        heating_mode = self._get_heating_mode(html)

        return TemperatureResult(temp_act, temp_set, heating_mode)

    def _get_heating_mode(self, contents: str):
        match = require_match(r"AWSCaseImage1v=(\d)", contents, "heating mode")
        value = match.group(1)
        value_number = int(value)
        return HeatingMode(value_number)
