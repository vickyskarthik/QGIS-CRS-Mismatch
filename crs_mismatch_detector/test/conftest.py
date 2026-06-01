# -*- coding: utf-8 -*-
"""
conftest.py — pytest fixtures for CRS Mismatch Detector tests.

All fixtures that require a running QGIS application are marked with
the `qgis_app` fixture provided by qgis-plugin-testing or pytest-qgis.

Tests that only test pure logic (e.g. _compute_mismatch) can run
without a full QGIS application by mocking the CRS objects.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# CRS factory helpers — used by both unit and integration tests
# ---------------------------------------------------------------------------


def make_crs(auth_id: str):
    """Create a QgsCoordinateReferenceSystem from an authority ID string.

    Args:
        auth_id: e.g. 'EPSG:4326', 'EPSG:32644'.

    Returns:
        QgsCoordinateReferenceSystem instance (may be invalid if auth_id unknown).
    """
    from qgis.core import QgsCoordinateReferenceSystem

    crs = QgsCoordinateReferenceSystem(auth_id)
    return crs


def make_memory_vector_layer(crs_auth_id: str = "EPSG:4326", name: str = "test_layer"):
    """Create an in-memory point layer for testing.

    Args:
        crs_auth_id: CRS authority ID for the layer.
        name:        Layer name.

    Returns:
        QgsVectorLayer (memory provider).
    """
    from qgis.core import QgsVectorLayer

    uri = f"Point?crs={crs_auth_id}&field=id:integer&field=name:string"
    layer = QgsVectorLayer(uri, name, "memory")
    assert layer.isValid(), f"Could not create memory layer with CRS {crs_auth_id}"
    return layer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def crs_4326():
    """Return EPSG:4326 CRS."""
    return make_crs("EPSG:4326")


@pytest.fixture
def crs_32644():
    """Return EPSG:32644 (UTM zone 44N) CRS."""
    return make_crs("EPSG:32644")


@pytest.fixture
def crs_3857():
    """Return EPSG:3857 (Web Mercator) CRS."""
    return make_crs("EPSG:3857")


@pytest.fixture
def invalid_crs():
    """Return an invalid QgsCoordinateReferenceSystem."""
    from qgis.core import QgsCoordinateReferenceSystem

    return QgsCoordinateReferenceSystem()


@pytest.fixture
def clean_project(crs_32644):
    """Return a clean QgsProject with CRS set to EPSG:32644.

    Removes all layers after the test to avoid test pollution.
    """
    from qgis.core import QgsProject

    project = QgsProject.instance()
    project.clear()
    project.setCrs(crs_32644)
    yield project
    project.clear()
