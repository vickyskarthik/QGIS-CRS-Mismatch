# CRS Mismatch Detector — QGIS Plugin

[![License: GPL v2](https://img.shields.io/badge/License-GPLv2-blue.svg)](LICENSE)
[![QGIS Minimum Version](https://img.shields.io/badge/QGIS-%3E%3D3.10-green.svg)](https://qgis.org)

Scan your QGIS project for layers whose CRS differs from the project CRS, get a clear report, and create safe reprojected copies — without ever modifying your original data.

---

## Why this plugin?

QGIS uses **on-the-fly reprojection** to display layers correctly even when they use different CRS values. This means your map can look fine while your data is silently inconsistent. CRS differences can affect:

- Distance and area measurements
- Buffering and offset operations
- Spatial overlays and intersections
- Spatial joins and queries
- Raster processing and resampling
- Data export and interoperability

CRS Mismatch Detector finds these issues before they affect your analysis.

---

## Features

- **Scan all layers** — detects CRS differences across all vector and raster layers.
- **Robust CRS comparison** — does not rely only on `authid()` string matching; handles custom USER CRS, invalid CRS, and edge cases correctly.
- **Clear dialog table** — shows layer name, type, layer CRS, project CRS, mismatch type, and status at a glance.
- **Per-row reprojection** — click Reproject on any mismatched layer to create a corrected copy.
- **Batch reprojection** — reproject all mismatched layers in one click (with confirmation).
- **Auto-scan on project open** — optional warning when a project with CRS mismatches is opened.
- **New layer warning** — warns when a newly added layer has a CRS that differs from the project CRS.
- **Original data is never modified** — all reprojected outputs are new files with unique names.
- **Temporary output warning** — clearly informs you when output is a temporary file.

---

## Installation

### From QGIS Plugin Manager (recommended)

1. Open QGIS.
2. Go to: `Plugins → Manage and Install Plugins`
3. Search for: `CRS Mismatch Detector`
4. Click **Install Plugin**.

### From ZIP (testing builds)

1. Open QGIS.
2. Go to: `Plugins → Manage and Install Plugins → Install from ZIP`
3. Select the plugin ZIP file.
4. Click **Install Plugin**.
5. Enable the plugin in the plugin list.

### For Developers (local install)

```bash
# Copy the plugin package folder to your QGIS profile plugins directory
cp -r plugin/crs_mismatch_detector ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/

# Reload in QGIS using Plugin Reloader, or restart QGIS
```

---

## Usage

1. Open a QGIS project.
2. Go to: `Plugins → CRS Mismatch Detector → Check CRS Mismatches`  
   or click the toolbar button.
3. Click **Refresh** to scan layers.
4. Review the results table.
5. Click **Reproject** next to any mismatched layer to create a corrected copy.
6. Export the reprojected layer permanently if you want to keep it.

See [docs/INSTALLATION_AND_USAGE.md](docs/INSTALLATION_AND_USAGE.md) for the full user manual.

---

## Requirements

| Requirement | Version |
|---|---|
| QGIS | ≥ 3.10 |
| Python | ≥ 3.6 |
| External dependencies | None |

---

## Project Structure

```
plugin/
├── crs_mismatch_detector/
│   ├── metadata.txt              Plugin metadata (QGIS)
│   ├── __init__.py               QGIS plugin entry point
│   ├── crs_mismatch_detector.py  Plugin lifecycle, signals, menu, toolbar
│   ├── crs_checker.py            CRS comparison and scanning logic
│   ├── crs_mismatch_dialog.py    Dialog behaviour
│   ├── crs_mismatch_dialog_base.ui  Qt Designer UI file
│   ├── utils.py                  Reprojection utilities
│   ├── compat.py                 QGIS version compatibility shims
│   ├── resources.qrc             Qt resource file
│   ├── resources_rc.py           Generated resource module (stub)
│   ├── icons/
│   │   └── icon.png              Plugin icon
│   └── test/
│       ├── conftest.py           pytest fixtures
│       ├── test_crs_checker.py   Unit tests — CRS logic
│       └── test_reproject.py     Integration tests — reprojection
├── docs/
│   └── INSTALLATION_AND_USAGE.md
├── reports/                      Test results and review reports
├── .gitignore
├── setup.cfg
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## Running Tests

Tests require a running QGIS application with the Processing framework.

```bash
# Using pytest-qgis (recommended)
pip install pytest-qgis
cd plugin
python -m pytest crs_mismatch_detector/test/ -v

# Run only unit tests (faster, no Processing required)
python -m pytest crs_mismatch_detector/test/test_crs_checker.py -v

# Run with coverage
python -m pytest crs_mismatch_detector/test/ --cov=crs_mismatch_detector -v
```

---

## Lint

```bash
flake8 crs_mismatch_detector/ --max-line-length=100 --exclude=resources_rc.py
black --check crs_mismatch_detector/ --line-length 100 --exclude="resources_rc.py"
isort --check-only crs_mismatch_detector/ --skip resources_rc.py
```

---

## Packaging

To build a release ZIP for the QGIS Plugin Manager:

```bash
# Install qgis-plugin-ci
pip install qgis-plugin-ci

# Generate resources_rc.py first
pyrcc5 crs_mismatch_detector/resources.qrc -o crs_mismatch_detector/resources_rc.py

# Package
qgis-plugin-ci package 1.0.0
```

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[GNU General Public License v2 or later](LICENSE)
