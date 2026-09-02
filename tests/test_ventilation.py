import unittest
from unittest.mock import AsyncMock, patch

from amit_hvac_control.api.utils import SettingNotConfirmedException
from amit_hvac_control.api.ventilation import VentilationApi, VentilationResult
from amit_hvac_control.models import VentilationMode


def _result(ventilation_mode: VentilationMode, ventilation_speed: VentilationMode) -> VentilationResult:
    return VentilationResult(
        ventilation_mode=ventilation_mode,
        ventilation_speed=ventilation_speed,
        co2_current=500,
        co2_setpoint=800,
        air_temp_current=21.0,
        air_temp_setpoint=21.0,
        heating_level=0,
    )


class VentilationSetModeConfirmationTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_true_once_the_relay_bits_reflect_the_new_speed(self):
        # Mirrors the real-world report: the HMI's mode label flips to OFF
        # right away (an echo of the accepted POST), but the fan itself -
        # reflected by the bit-derived ventilation_speed - keeps running for
        # a beat before actually stopping.
        api = VentilationApi(session=None)
        api._async_save = AsyncMock(return_value=True)
        api.async_get_data = AsyncMock(
            side_effect=[
                _result(VentilationMode.OFF, VentilationMode.MEDIUM),
                _result(VentilationMode.OFF, VentilationMode.OFF),
            ]
        )

        with patch("amit_hvac_control.api.utils.asyncio.sleep", AsyncMock()):
            result = await api.async_set_ventilation(VentilationMode.OFF)

        self.assertTrue(result)
        self.assertEqual(api.async_get_data.await_count, 2)

    async def test_raises_when_the_relay_bits_never_confirm_the_new_speed(self):
        api = VentilationApi(session=None)
        api._async_save = AsyncMock(return_value=True)
        api.async_get_data = AsyncMock(
            return_value=_result(VentilationMode.OFF, VentilationMode.MEDIUM)
        )

        with patch("amit_hvac_control.api.utils.asyncio.sleep", AsyncMock()):
            with self.assertRaises(SettingNotConfirmedException):
                await api.async_set_ventilation(VentilationMode.OFF)

    async def test_auto_is_confirmed_via_the_mode_label_since_speed_varies(self):
        # AUTO has no fixed relay speed to check against, so confirmation
        # falls back to the selected-mode label instead.
        api = VentilationApi(session=None)
        api._async_save = AsyncMock(return_value=True)
        api.async_get_data = AsyncMock(
            return_value=_result(VentilationMode.AUTO, VentilationMode.LOW)
        )

        result = await api.async_set_ventilation(VentilationMode.AUTO)

        self.assertTrue(result)


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
