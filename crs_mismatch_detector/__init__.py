# -*- coding: utf-8 -*-
"""
CRS Mismatch Detector — QGIS Plugin

Entry point required by QGIS plugin loader.
"""


def classFactory(iface):  # noqa: N802
    """Load the plugin class from the main module.

    Args:
        iface: A QGIS interface instance.

    Returns:
        CrsMismatchDetector plugin instance.
    """
    from .crs_mismatch_detector import CrsMismatchDetector

    return CrsMismatchDetector(iface)
