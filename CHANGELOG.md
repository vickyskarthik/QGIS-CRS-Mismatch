# Changelog — CRS Mismatch Detector

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2026-06-01

### Added

- Initial production release.
- Robust CRS mismatch detection (not relying only on `authid()` comparison).
- Handles invalid layer CRS, invalid project CRS, custom USER CRS, empty projects.
- Dialog table showing: layer name, type, layer CRS, project CRS, mismatch type, status, and action.
- Per-row Reproject button keyed on stable layer ID (not row index).
- Reproject All Mismatched Layers with confirmation and progress dialog.
- Auto-scan on project open (optional, persisted in QgsSettings).
- New-layer-added warning with Details button.
- Safe reprojection: vector via `native:reprojectlayer`, raster via `gdal:warpreproject`.
- Unique output filenames with UUID fragment to prevent overwrite.
- Explicit `SOURCE_CRS` for raster reprojection.
- Temporary output warning after every reprojection.
- Show All / mismatches-only toggle.
- Copy Layer CRS / Copy Project CRS context menu.
- CRS tooltips on truncated cells.
- Automatic signal cleanup on plugin unload.
- Plugin reload safety — no duplicate menu entries or warnings.
- QGIS version compatibility shims (3.10 – 3.40+).
- Unit tests for all CRS logic paths.
- Integration tests for vector reprojection, removed layer, invalid project CRS.
- pytest fixtures and test data structure.
- Full user manual and installation guide.
