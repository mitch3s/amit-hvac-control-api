"""Interactive TUI for manually exercising the Amit HVAC control API against a real device.

Not part of the published package - run directly from the repo, e.g.:
    uv run scripts/tui.py --host=http://192.168.1.80 --username=root --password=amit
"""

from __future__ import annotations

import argparse

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Log, Select, Static, TabbedContent, TabPane

from amit_hvac_control.client import AmitHvacControlClient
from amit_hvac_control.models import Config, HeatingMode, Season, VentilationMode


class AmitTuiApp(App):
    CSS = """
    TabbedContent {
        height: 1fr;
    }
    TabPane {
        layout: horizontal;
    }
    .values-pane, .controls-pane {
        height: 1fr;
        width: 1fr;
        border: round $accent;
        padding: 1 2;
    }
    .controls-pane > Horizontal {
        height: auto;
        margin-bottom: 1;
    }
    .controls-pane > Horizontal > Input, .controls-pane > Horizontal > Select {
        width: 1fr;
    }
    .controls-pane > Button {
        margin-bottom: 1;
    }
    Log {
        height: 10;
        border: round $accent;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, config: Config):
        super().__init__()
        self._config = config
        self.client: AmitHvacControlClient | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Status", id="tab-status"):
                with VerticalScroll(classes="values-pane") as values_pane:
                    values_pane.border_title = "Current values"
                    yield Static("Loading...", id="status-output")
                with VerticalScroll(classes="controls-pane") as controls_pane:
                    controls_pane.border_title = "Controls"
                    yield Button("Refresh", id="status-refresh")
            with TabPane("Temperature", id="tab-temperature"):
                with VerticalScroll(classes="values-pane") as values_pane:
                    values_pane.border_title = "Current values"
                    yield Static("Loading...", id="temperature-output")
                with VerticalScroll(classes="controls-pane") as controls_pane:
                    controls_pane.border_title = "Controls"
                    yield Button("Refresh", id="temperature-refresh")
                    with Horizontal():
                        yield Input(placeholder="Target temperature, e.g. 21.5", id="temp-set-input")
                        yield Button("Set temperature", id="temp-set-btn")
                    with Horizontal():
                        yield Input(placeholder="Minimal temperature, e.g. 16.0", id="temp-min-input")
                        yield Button("Set minimal temp", id="temp-min-btn")
                    with Horizontal():
                        yield Select[HeatingMode](
                            [(m.name, m) for m in HeatingMode], id="heating-mode-select", allow_blank=False
                        )
                        yield Button("Set heating mode", id="heating-mode-btn")
                    with Horizontal():
                        yield Select[Season](
                            [(s.name, s) for s in Season], id="season-select", allow_blank=False
                        )
                        yield Button("Set season", id="season-btn")
            with TabPane("Ventilation", id="tab-ventilation"):
                with VerticalScroll(classes="values-pane") as values_pane:
                    values_pane.border_title = "Current values"
                    yield Static("Loading...", id="ventilation-output")
                with VerticalScroll(classes="controls-pane") as controls_pane:
                    controls_pane.border_title = "Controls"
                    yield Button("Refresh", id="ventilation-refresh")
                    with Horizontal():
                        yield Select[VentilationMode](
                            [(m.name, m) for m in VentilationMode],
                            id="ventilation-mode-select",
                            allow_blank=False,
                        )
                        yield Button("Set ventilation mode", id="ventilation-mode-btn")
                    with Horizontal():
                        yield Input(placeholder="Target air temperature, e.g. 21.0", id="ventilation-temp-input")
                        yield Button("Set target temp", id="ventilation-temp-btn")
                    with Horizontal():
                        yield Input(placeholder="Target CO2, e.g. 800", id="ventilation-co2-input")
                        yield Button("Set target CO2", id="ventilation-co2-btn")
        yield Log(id="log")
        yield Footer()

    async def on_mount(self) -> None:
        self.client = AmitHvacControlClient(self._config)
        await self.client.__aenter__()
        self._log(f"Connected to {self._config.url}")
        await self._refresh_status()
        await self._refresh_temperature()
        await self._refresh_ventilation()

    async def on_unmount(self) -> None:
        if self.client is not None:
            await self.client.__aexit__(None, None, None)

    def _log(self, message: str) -> None:
        self.query_one("#log", Log).write_line(message)

    async def _refresh_status(self) -> None:
        try:
            data = await self.client.status_api.async_get_overview()
            self.query_one("#status-output", Static).update(str(data))
        except Exception as err:
            self._log(f"Refresh status: FAILED - {err}")

    async def _refresh_temperature(self) -> None:
        try:
            data = await self.client.temperature_api.async_get_data()
            self.query_one("#temperature-output", Static).update(str(data))
        except Exception as err:
            self._log(f"Refresh temperature: FAILED - {err}")

    async def _refresh_ventilation(self) -> None:
        try:
            data = await self.client.ventilation_api.async_get_data()
            self.query_one("#ventilation-output", Static).update(str(data))
        except Exception as err:
            self._log(f"Refresh ventilation: FAILED - {err}")

    async def _run_action(self, description: str, coro) -> None:
        try:
            result = await coro
            self._log(f"{description}: ok ({result})")
        except Exception as err:
            self._log(f"{description}: FAILED - {err}")

    @on(Button.Pressed, "#status-refresh")
    async def handle_status_refresh(self) -> None:
        await self._refresh_status()
        self._log("Status refreshed")

    @on(Button.Pressed, "#temperature-refresh")
    async def handle_temperature_refresh(self) -> None:
        await self._refresh_temperature()
        self._log("Temperature refreshed")

    @on(Button.Pressed, "#ventilation-refresh")
    async def handle_ventilation_refresh(self) -> None:
        await self._refresh_ventilation()
        self._log("Ventilation refreshed")

    @on(Button.Pressed, "#temp-set-btn")
    async def handle_temp_set(self) -> None:
        raw = self.query_one("#temp-set-input", Input).value
        try:
            value = float(raw)
        except ValueError:
            self._log(f"Set temperature: invalid value '{raw}'")
            return
        await self._run_action(
            f"Set temperature to {value}", self.client.temperature_api.async_set_temperature(value)
        )
        await self._refresh_temperature()

    @on(Button.Pressed, "#temp-min-btn")
    async def handle_temp_min(self) -> None:
        raw = self.query_one("#temp-min-input", Input).value
        try:
            value = float(raw)
        except ValueError:
            self._log(f"Set minimal temperature: invalid value '{raw}'")
            return
        await self._run_action(
            f"Set minimal temperature to {value}",
            self.client.temperature_api.async_set_minimal_temperature(value),
        )
        await self._refresh_temperature()

    @on(Button.Pressed, "#heating-mode-btn")
    async def handle_heating_mode(self) -> None:
        mode: HeatingMode = self.query_one("#heating-mode-select", Select).value
        await self._run_action(
            f"Set heating mode to {mode.name}", self.client.temperature_api.async_set_heating_mode(mode)
        )
        await self._refresh_temperature()

    @on(Button.Pressed, "#season-btn")
    async def handle_season(self) -> None:
        season: Season = self.query_one("#season-select", Select).value
        await self._run_action(
            f"Set season to {season.name}", self.client.temperature_api.async_set_season(season)
        )
        await self._refresh_temperature()
        await self._refresh_status()

    @on(Button.Pressed, "#ventilation-mode-btn")
    async def handle_ventilation_mode(self) -> None:
        mode: VentilationMode = self.query_one("#ventilation-mode-select", Select).value
        await self._run_action(
            f"Set ventilation mode to {mode.name}", self.client.ventilation_api.async_set_ventilation(mode)
        )
        await self._refresh_ventilation()
        await self._refresh_status()

    @on(Button.Pressed, "#ventilation-temp-btn")
    async def handle_ventilation_temp(self) -> None:
        raw = self.query_one("#ventilation-temp-input", Input).value
        try:
            value = float(raw)
        except ValueError:
            self._log(f"Set target air temperature: invalid value '{raw}'")
            return
        await self._run_action(
            f"Set target air temperature to {value}",
            self.client.ventilation_api.async_set_target_air_temperature(value),
        )
        await self._refresh_ventilation()

    @on(Button.Pressed, "#ventilation-co2-btn")
    async def handle_ventilation_co2(self) -> None:
        raw = self.query_one("#ventilation-co2-input", Input).value
        try:
            value = int(raw)
        except ValueError:
            self._log(f"Set target CO2: invalid value '{raw}'")
            return
        await self._run_action(
            f"Set target CO2 to {value}", self.client.ventilation_api.async_set_target_co2(value)
        )
        await self._refresh_ventilation()


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive TUI for testing the Amit HVAC control API")
    parser.add_argument("--host", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    config = Config(args.host, args.username, args.password)
    AmitTuiApp(config).run()


if __name__ == "__main__":
    main()
