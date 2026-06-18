# Amit HVAC Control

Library for controlling Amit HVAC solution using the web server as an interface. It works by scraping the HMI web pages and sending POST requests for save operations.

Only works with the specifically developed machine logic runtime application for the following hardware:

- AMiNi4W2 PLC
- AMR-OP70RHC/04 Wall-mounted controller

## Run

Run the main file with arguments to test the connection nd retrieve all data.

```bash
uv run ./src/amit_hvac_control/__main__.py --host=<internal_network_address> --username=<username> --password=<password>
```

## Build

```bash
uv build
```

## Release

Releases are published automatically by [.github/workflows/release.yml](.github/workflows/release.yml).

1. Bump the `version` in [pyproject.toml](pyproject.toml) and move the `Unreleased` entries in [CHANGELOG.md](CHANGELOG.md) under a new version heading.
2. Merge that change into `main`.
3. Tag the merge commit and push the tag, e.g.:
   ```bash
   git tag v0.4.0
   git push origin v0.4.0
   ```
4. The workflow builds the package, publishes it to PyPI, and creates the matching GitHub Release.
