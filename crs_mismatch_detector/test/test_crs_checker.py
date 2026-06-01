# -*- coding: utf-8 -*-
"""
test_crs_checker.py — Unit tests for crs_checker.py.

Test IDs follow the Testing Plan in TESTING_PLAN.md.

These tests exercise the CRS comparison logic in isolation.
A live QGIS application (QgsApplication) must be initialised before
running these tests.  When using pytest-qgis, that is done automatically.

Run:
    python -m pytest crs_mismatch_detector/test/test_crs_checker.py -v
"""

from __future__ import annotations

# The plugin's crs_checker module is imported inside each test to avoid
# import-time issues when pytest is collected outside QGIS.
# When running inside QGIS (e.g. with pytest-qgis), the import works normally.


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _checker():
    """Import and return the crs_checker module."""
    from crs_mismatch_detector import crs_checker  # noqa: F401

    return crs_checker


def _make_crs(auth_id: str):
    from qgis.core import QgsCoordinateReferenceSystem

    return QgsCoordinateReferenceSystem(auth_id)


def _make_invalid_crs():
    from qgis.core import QgsCoordinateReferenceSystem

    return QgsCoordinateReferenceSystem()


# ---------------------------------------------------------------------------
# T-01 — EPSG CRS mismatch
# ---------------------------------------------------------------------------


def test_T01_epsg_mismatch():
    """T-01: Layer EPSG:4326 vs project EPSG:32644 → mismatch=True."""
    checker = _checker()
    layer_crs = _make_crs("EPSG:4326")
    project_crs = _make_crs("EPSG:32644")

    assert layer_crs.isValid(), "Layer CRS should be valid"
    assert project_crs.isValid(), "Project CRS should be valid"
    assert checker._compute_mismatch(layer_crs, project_crs) is True


# ---------------------------------------------------------------------------
# T-02 — Same CRS
# ---------------------------------------------------------------------------


def test_T02_same_crs():
    """T-02: Layer EPSG:32644 vs project EPSG:32644 → mismatch=False."""
    checker = _checker()
    crs = _make_crs("EPSG:32644")

    assert checker._compute_mismatch(crs, crs) is False


def test_T02b_same_crs_different_instances():
    """T-02b: Two separate EPSG:32644 instances → mismatch=False."""
    checker = _checker()
    crs_a = _make_crs("EPSG:32644")
    crs_b = _make_crs("EPSG:32644")

    assert checker._compute_mismatch(crs_a, crs_b) is False


# ---------------------------------------------------------------------------
# T-03 — Invalid layer CRS
# ---------------------------------------------------------------------------


def test_T03_invalid_layer_crs():
    """T-03: Invalid layer CRS → mismatch=False, no crash."""
    checker = _checker()
    invalid = _make_invalid_crs()
    project_crs = _make_crs("EPSG:32644")

    result = checker._compute_mismatch(invalid, project_crs)
    assert result is False  # safety: cannot determine mismatch with invalid CRS


# ---------------------------------------------------------------------------
# T-04 — Invalid project CRS
# ---------------------------------------------------------------------------


def test_T04_invalid_project_crs():
    """T-04: Invalid project CRS → mismatch=False, no crash."""
    checker = _checker()
    layer_crs = _make_crs("EPSG:4326")
    invalid = _make_invalid_crs()

    result = checker._compute_mismatch(layer_crs, invalid)
    assert result is False


# ---------------------------------------------------------------------------
# T-05 — Empty project
# ---------------------------------------------------------------------------


def test_T05_empty_project():
    """T-05: Scanning an empty project → empty list, no crash."""
    from qgis.core import QgsProject

    checker = _checker()
    project = QgsProject.instance()
    project.clear()

    results = checker.scan_all_layers(project)
    assert isinstance(results, list)
    assert len(results) == 0


# ---------------------------------------------------------------------------
# T-07 — CRS display string
# ---------------------------------------------------------------------------


def test_T07_crs_display_string_contains_authid():
    """T-07: Display string for EPSG:4326 must contain the authid."""
    checker = _checker()
    crs = _make_crs("EPSG:4326")

    display = checker._crs_display_string(crs)
    assert "EPSG:4326" in display, f"Expected 'EPSG:4326' in display string, got: {display}"


def test_T07b_invalid_crs_display_string():
    """T-07b: Display string for invalid CRS should not crash and return a message."""
    checker = _checker()
    invalid = _make_invalid_crs()

    display = checker._crs_display_string(invalid)
    assert isinstance(display, str)
    assert len(display) > 0
    assert "Invalid" in display or "Unknown" in display


# ---------------------------------------------------------------------------
# T-08 — Mismatch type description
# ---------------------------------------------------------------------------


def test_T08_mismatch_type_different_authid():
    """T-08: Different EPSG codes → mismatch type 'Different authid'."""
    checker = _checker()
    crs_a = _make_crs("EPSG:4326")
    crs_b = _make_crs("EPSG:32644")

    mtype = checker._mismatch_type(crs_a, crs_b)
    assert mtype == "Different authid", f"Got: {mtype}"


def test_T08b_no_mismatch_type():
    """T-08b: Same CRS → mismatch type not triggered by _compute_mismatch."""
    checker = _checker()
    crs = _make_crs("EPSG:4326")

    # When there is no mismatch, _compute_mismatch returns False,
    # and the scan code sets mismatch_type to 'No mismatch'.
    is_mismatch = checker._compute_mismatch(crs, crs)
    assert is_mismatch is False


# ---------------------------------------------------------------------------
# T-08c — Invalid CRS mismatch type
# ---------------------------------------------------------------------------


def test_T08c_both_invalid_crs():
    """T-08c: Both CRS invalid → mismatch=False, mismatch_type = 'Both CRS invalid'."""
    checker = _checker()
    inv_a = _make_invalid_crs()
    inv_b = _make_invalid_crs()

    mismatch = checker._compute_mismatch(inv_a, inv_b)
    mtype = checker._mismatch_type(inv_a, inv_b)

    assert mismatch is False
    assert "invalid" in mtype.lower(), f"Got: {mtype}"


# ---------------------------------------------------------------------------
# Scan results — sorting, structure
# ---------------------------------------------------------------------------


def test_scan_returns_layercrsinfo_objects():
    """Scan results must be a list of LayerCrsInfo objects."""
    from qgis.core import QgsProject

    checker = _checker()
    project = QgsProject.instance()
    project.clear()
    project.setCrs(_make_crs("EPSG:32644"))

    # Add a mismatched layer
    from qgis.core import QgsVectorLayer

    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=id:integer", "test_layer", "memory")
    assert layer.isValid()
    project.addMapLayer(layer)

    results = checker.scan_all_layers(project)

    assert len(results) >= 1
    info = results[0]
    assert hasattr(info, "layer_id")
    assert hasattr(info, "layer_name")
    assert hasattr(info, "is_mismatch")
    assert info.is_mismatch is True

    project.clear()


def test_scan_mismatches_first():
    """Mismatched layers should appear first in the sorted results."""
    from qgis.core import QgsProject, QgsVectorLayer

    checker = _checker()
    project = QgsProject.instance()
    project.clear()
    project.setCrs(_make_crs("EPSG:32644"))

    match_layer = QgsVectorLayer(
        "Point?crs=EPSG:32644&field=id:integer", "aaa_match", "memory"
    )
    mismatch_layer = QgsVectorLayer(
        "Point?crs=EPSG:4326&field=id:integer", "zzz_mismatch", "memory"
    )
    project.addMapLayer(match_layer)
    project.addMapLayer(mismatch_layer)

    results = checker.scan_all_layers(project)
    assert len(results) == 2
    assert results[0].is_mismatch is True
    assert results[1].is_mismatch is False

    project.clear()


def test_get_mismatches_filter():
    """get_mismatches() must return only mismatched entries."""
    from qgis.core import QgsProject, QgsVectorLayer

    checker = _checker()
    project = QgsProject.instance()
    project.clear()
    project.setCrs(_make_crs("EPSG:32644"))

    project.addMapLayer(
        QgsVectorLayer("Point?crs=EPSG:4326&field=id:integer", "mis1", "memory")
    )
    project.addMapLayer(
        QgsVectorLayer("Point?crs=EPSG:32644&field=id:integer", "ok1", "memory")
    )

    results = checker.scan_all_layers(project)
    mismatches = checker.get_mismatches(results)

    assert all(m.is_mismatch for m in mismatches)
    assert len(mismatches) == 1
    assert mismatches[0].layer_name == "mis1"

    project.clear()


def test_get_layer_by_id():
    """get_layer_by_id() must return the live layer object."""
    from qgis.core import QgsProject, QgsVectorLayer

    checker = _checker()
    project = QgsProject.instance()
    project.clear()

    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=id:integer", "findme", "memory")
    project.addMapLayer(layer)

    found = checker.get_layer_by_id(layer.id(), project)
    assert found is not None
    assert found.name() == "findme"

    project.clear()


def test_get_layer_by_id_missing():
    """get_layer_by_id() must return None for an unknown ID."""
    from qgis.core import QgsProject

    checker = _checker()
    project = QgsProject.instance()
    project.clear()

    result = checker.get_layer_by_id("nonexistent_layer_id_xyz", project)
    assert result is None


def test_mismatch_count():
    """mismatch_count() must return the correct number of mismatched layers."""
    from qgis.core import QgsProject, QgsVectorLayer

    checker = _checker()
    project = QgsProject.instance()
    project.clear()
    project.setCrs(_make_crs("EPSG:32644"))

    project.addMapLayer(
        QgsVectorLayer("Point?crs=EPSG:4326&field=id:integer", "m1", "memory")
    )
    project.addMapLayer(
        QgsVectorLayer("Point?crs=EPSG:4326&field=id:integer", "m2", "memory")
    )
    project.addMapLayer(
        QgsVectorLayer("Point?crs=EPSG:32644&field=id:integer", "ok1", "memory")
    )

    count = checker.mismatch_count(project)
    assert count == 2

    project.clear()
