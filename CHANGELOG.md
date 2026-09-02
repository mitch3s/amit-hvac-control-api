# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `VentilationApi.async_set_ventilation`/`async_set_target_air_temperature`/`async_set_target_co2` and `TemperatureApi.async_set_temperature`/`async_set_heating_mode` now re-fetch device state after posting and retry (up to 3 attempts, 1s apart) until the controller actually reflects the change, instead of trusting a 2xx response alone. The device can ack a POST while silently dropping the change, which previously meant a setter could report success (`True`) while the physical state stayed unchanged. `async_set_ventilation` specifically confirms against the bit-derived `ventilation_speed` field (the relay status), not the `ventilation_mode` selection label, since the label can flip before the fan actually changes speed. Raises `amit_hvac_control.api.utils.SettingNotConfirmedException` if the change is never confirmed.

## [0.4.0] - 2026-06-18

### Fixed

- Corrected the minimum supported Python version and removed a bogus `asyncio` dependency.

## [0.3.3] - 2024-04-17

### Fixed

- Fixed a regression caused by the latest `aiohttp` release.

## [0.3.2] - 2024-04-16

### Added

- Added air temperature support.

## [0.3.1] - 2024-03-31

### Added

- Initial release: control Amit HVAC systems by scraping the HMI web interface and submitting save requests.

[Unreleased]: https://github.com/mitch3s/amit-hvac-control/compare/v0.3.3...HEAD
[0.3.3]: https://github.com/mitch3s/amit-hvac-control/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/mitch3s/amit-hvac-control/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/mitch3s/amit-hvac-control/releases/tag/v0.3.1
