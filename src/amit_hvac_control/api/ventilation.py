import math
import re
from typing import Callable, Optional
from aiohttp import ClientSession

from amit_hvac_control.api.parsing import (
    require_class,
    require_match,
    require_selector,
)
from amit_hvac_control.api.utils import async_save_and_confirm, get_multipart_data
from amit_hvac_control.models import VentilationMode
from bs4 import BeautifulSoup

VENTILATION_URL = "/pages/page00/Page002.hta"

class VentilationBitResults:
    def __init__(self, heating_on: bool, ventilation_speed: VentilationMode):
        self.heating_on = heating_on
        self.ventilation_speed = ventilation_speed

    def __str__(self):
        return f"""
Ventilation speed: {self.ventilation_speed.name}
Heating on: {self.heating_on}
"""

class VentilationResult:
    def __init__(
        self,
        ventilation_mode: VentilationMode,
        ventilation_speed: VentilationMode,
        co2_current: float,
        co2_setpoint: float,
        air_temp_current: float,
        air_temp_setpoint: float,
        heating_level: float
    ):
        self.ventilation_mode = ventilation_mode
        self.ventilation_speed = ventilation_speed
        self.co2_current = co2_current
        self.co2_setpoint = co2_setpoint
        self.air_temp_current = air_temp_current
        self.air_temp_setpoint = air_temp_setpoint
        self.heating_level = heating_level
        self.heating_on = heating_level > 0

    def __str__(self):
        return f"""
Ventilation mode: {self.ventilation_mode.name}
Ventilation speed: {self.ventilation_speed.name}
CO2 Current: {self.co2_current}
CO2 Setpoint: {self.co2_setpoint}
Air temperature Current: {self.air_temp_current}
Air temperature Setpoint: {self.air_temp_setpoint}
Heating on: {self.heating_on}
Heating level: {self.heating_level}
"""


class VentilationApi:
    """Ventilation API."""

    def __init__(self, session: ClientSession):
        self.session = session

    async def async_get_data(self):
        async with self.session.get(VENTILATION_URL) as response:
            content = await response.read()
            return self._extract_data(content)

    async def async_set_ventilation(
        self,
        ventilation_mode: VentilationMode,
        on_retry: Optional[Callable[[int, Optional[VentilationResult]], None]] = None,
    ):
        button_val = ventilation_mode.get_button()

        # POST request
        post_data = {
            "SET_i1w4074s255t32j1k1g2": 0,
            "SET_i1w4074s255t32j1k1g3": 1,
            "SET_i1w4074s255t32j1k1g4": 2,
            "SET_i1w4074s255t32j1k1g5": 3,
            "SET_i1w4074s255t32j1k1g6": 4,
            button_val: "",
        }

        return await async_save_and_confirm(
            save=lambda: self._async_save(post_data),
            fetch=self.async_get_data,
            is_applied=lambda data: self._ventilation_mode_applied(data, ventilation_mode),
            on_retry=on_retry,
        )

    def _ventilation_mode_applied(self, data: VentilationResult, ventilation_mode: VentilationMode) -> bool:
        # `ventilation_mode` (AWSCaseLabel1v) is the HMI's selected-mode label -
        # it can flip as soon as the device accepts the POST, before the fan
        # relay actually changes. `ventilation_speed` is derived from the
        # AWSCaseLabelBit AND'd status bits, which reflects the real relay
        # state, so it's the trustworthy signal for OFF/LOW/MEDIUM/HIGH. AUTO
        # has no fixed speed to check against (it varies with CO2/demand), so
        # for AUTO we fall back to the selection label.
        if ventilation_mode == VentilationMode.AUTO:
            return data.ventilation_mode == VentilationMode.AUTO
        return data.ventilation_speed == ventilation_mode

    async def async_set_target_air_temperature(
        self,
        temp: float,
        on_retry: Optional[Callable[[int, Optional[VentilationResult]], None]] = None,
    ):
        post_data = {
            "NUMEDIT_i1w4095s255t2j1k1g7a15.00m30.00": temp,
            "BTNSUB_g7": "Zapsat",
        }
        return await async_save_and_confirm(
            save=lambda: self._async_save(post_data),
            fetch=self.async_get_data,
            is_applied=lambda data: math.isclose(data.air_temp_setpoint, temp, abs_tol=0.05),
            on_retry=on_retry,
        )

    async def async_set_target_co2(
        self,
        co2: int,
        on_retry: Optional[Callable[[int, Optional[VentilationResult]], None]] = None,
    ):
        post_data = {
            "NUMEDIT_i1w4087s255t2j1k1g8a100m1000": co2,
            "BTNSUB_g8": "Zapsat"
        }
        return await async_save_and_confirm(
            save=lambda: self._async_save(post_data),
            fetch=self.async_get_data,
            is_applied=lambda data: math.isclose(data.co2_setpoint, co2, abs_tol=0.5),
            on_retry=on_retry,
        )

    async def _async_save(self, post: dict):
        data = get_multipart_data(post)
        
        async with await self.session.post(VENTILATION_URL, data=data) as response:
            return response.ok

    def _extract_data(self, content: bytes):
        soup = BeautifulSoup(content, "html.parser")

        co2_current_el = require_selector(
            soup, ".AWNumericView1,.AWNumericView1-alert-max", "current CO2 value"
        )
        co2_current = float(co2_current_el.text)

        air_temp_current_el = require_class(
            soup, "AWNumericView2", "current air temperature"
        )
        air_temp_current = float(air_temp_current_el.text)

        air_temp_setpoint_input_el = require_selector(
            soup, "input.AWNumericEditButton1", "air temperature setpoint"
        )
        air_temp_setpoint = float(air_temp_setpoint_input_el.attrs["value"])

        co2_setpoint_input_el = require_selector(
            soup, "input.AWNumericEditButton2", "CO2 setpoint"
        )
        co2_setpoint = float(co2_setpoint_input_el.attrs["value"])

        html = str(soup)
        ventilation_mode = self._get_ventilation_mode(html)
        heating_level = self._get_heating_level(html)
        bit_fields = self._get_bit_fields(html)

        return VentilationResult(
            ventilation_mode,
            bit_fields.ventilation_speed,
            co2_current,
            co2_setpoint,
            air_temp_current,
            air_temp_setpoint,
            heating_level
        )

    def _get_ventilation_mode(self, contents: str):
        match = require_match(r"AWSCaseLabel1v=(\d)", contents, "ventilation mode")
        value = match.group(1)
        value_number = int(value)
        return VentilationMode(value_number)

    def _get_heating_level(self, contents: str):
        match = require_match(r"AWProgressBar1v=(\d+.\d+)", contents, "heating level")
        value = match.group(1)
        return float(value)

    def _get_bit_fields(self, contents: str):
        results = {}

        matches = re.findall(r"AWSCaseLabelBit(\d)_.*\((\d+)&(\d+)\)", contents)
        for key, b1, b2 in matches:
            bit_and = int(b1) & int(b2)
            results[int(key)] = bit_and > 0

        ventilation_speed: VentilationMode = VentilationMode.OFF
        if results.get(2, False):
            ventilation_speed = VentilationMode.LOW
        elif results.get(3, False):
            ventilation_speed = VentilationMode.MEDIUM
        elif results.get(4, False):
            ventilation_speed = VentilationMode.HIGH

        return VentilationBitResults(
            results.get(1, False),
            ventilation_speed
        )
