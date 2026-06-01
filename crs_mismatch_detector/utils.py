# -*- coding: utf-8 -*-
"""
utils.py — Reprojection utilities for CRS Mismatch Detector.

Responsibilities:
  - Generate safe, unique output file paths.
  - Reproject vector layers via native:reprojectlayer.
  - Reproject raster layers via gdal:warpreproject.
  - Validate and load output layers into the QGIS project.
  - Log all reprojection events.

NOTE: `processing` is imported lazily (inside functions) to comply with
QGIS plugin loading rules and the project CLAUDE_AGENT_RULES.md.
"""

from __future__ import annotations

import os
import re
import tempfile
import uuid
from typing import Tuple

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)

from .compat import LAYER_TYPE_RASTER, LAYER_TYPE_VECTOR

LOG_TAG = "CRS Mismatch Detector"

# Temporary warning shown after every reprojection
TEMP_OUTPUT_WARNING = (
    "The reprojected layer was added as a temporary file. "
    "Export it permanently if you want to keep it."
)


# ---------------------------------------------------------------------------
# Safe output filename
# ---------------------------------------------------------------------------


def _safe_filename(name: str) -> str:
    """Convert an arbitrary layer name into a filesystem-safe filename stem.

    Rules:
      - Replace non-alphanumeric characters with underscores.
      - Truncate to 40 characters.
      - Append 8-character UUID hex fragment for uniqueness.

    Args:
        name: Raw layer name.

    Returns:
        A filesystem-safe filename stem without extension.
    """
    safe = re.sub(r"[^\w]", "_", name)
    safe = re.sub(r"_+", "_", safe).strip("_")
    safe = safe[:40] if len(safe) > 40 else safe
    uid = uuid.uuid4().hex[:8]
    return f"{safe}_{uid}"


def _make_output_path(layer_name: str, extension: str) -> str:
    """Build a unique temporary output path.

    Args:
        layer_name: Name of the source layer.
        extension:  File extension including dot, e.g. '.gpkg' or '.tif'.

    Returns:
        Full absolute path inside the system temp directory.
    """
    stem = _safe_filename(layer_name)
    return os.path.join(tempfile.gettempdir(), f"{stem}_reprojected{extension}")


# ---------------------------------------------------------------------------
# Vector reprojection
# ---------------------------------------------------------------------------


def _reproject_vector(layer, target_crs, output_path: str) -> Tuple[bool, str]:
    """Reproject a vector layer using native:reprojectlayer.

    Args:
        layer:       QgsVectorLayer to reproject.
        target_crs:  QgsCoordinateReferenceSystem — target CRS.
        output_path: Full path for the output file.

    Returns:
        (success: bool, message: str)
    """
    import processing  # lazy import — required by plugin rules

    QgsMessageLog.logMessage(
        f"Reprojecting vector '{layer.name()}' → {target_crs.authid()} at '{output_path}'",
        LOG_TAG,
        Qgis.Info,
    )

    try:
        result = processing.run(
            "native:reprojectlayer",
            {
                "INPUT": layer,
                "TARGET_CRS": target_crs,
                "OUTPUT": output_path,
            },
        )
        out_path = result.get("OUTPUT", "")
        if not out_path:
            msg = f"native:reprojectlayer returned no output path for '{layer.name()}'."
            QgsMessageLog.logMessage(msg, LOG_TAG, Qgis.Critical)
            return False, msg

        QgsMessageLog.logMessage(
            f"Vector reprojection succeeded for '{layer.name()}'.",
            LOG_TAG,
            Qgis.Info,
        )
        return True, out_path

    except Exception as exc:
        msg = f"Vector reprojection failed for '{layer.name()}': {exc}"
        QgsMessageLog.logMessage(msg, LOG_TAG, Qgis.Critical)
        return False, str(exc)


# ---------------------------------------------------------------------------
# Raster reprojection
# ---------------------------------------------------------------------------


def _reproject_raster(layer, target_crs, output_path: str) -> Tuple[bool, str]:
    """Reproject a raster layer using gdal:warpreproject.

    Args:
        layer:       QgsRasterLayer to reproject.
        target_crs:  QgsCoordinateReferenceSystem — target CRS.
        output_path: Full path for the output file.

    Returns:
        (success: bool, message: str)
    """
    import processing  # lazy import — required by plugin rules

    QgsMessageLog.logMessage(
        f"Reprojecting raster '{layer.name()}' → {target_crs.authid()} at '{output_path}'",
        LOG_TAG,
        Qgis.Info,
    )

    try:
        result = processing.run(
            "gdal:warpreproject",
            {
                "INPUT": layer,
                "SOURCE_CRS": layer.crs(),  # explicitly required for rasters
                "TARGET_CRS": target_crs,
                "RESAMPLING": 0,            # Nearest neighbour
                "NODATA": None,
                "TARGET_RESOLUTION": None,
                "OPTIONS": "COMPRESS=LZW",
                "DATA_TYPE": 0,             # Use input data type
                "TARGET_EXTENT": None,
                "TARGET_EXTENT_CRS": None,
                "MULTITHREADING": False,
                "EXTRA": "",
                "OUTPUT": output_path,
            },
        )
        out_path = result.get("OUTPUT", "")
        if not out_path:
            msg = f"gdal:warpreproject returned no output path for '{layer.name()}'."
            QgsMessageLog.logMessage(msg, LOG_TAG, Qgis.Critical)
            return False, msg

        QgsMessageLog.logMessage(
            f"Raster reprojection succeeded for '{layer.name()}'.",
            LOG_TAG,
            Qgis.Info,
        )
        return True, out_path

    except Exception as exc:
        msg = f"Raster reprojection failed for '{layer.name()}': {exc}"
        QgsMessageLog.logMessage(msg, LOG_TAG, Qgis.Critical)
        return False, str(exc)


# ---------------------------------------------------------------------------
# Public reprojection entry point
# ---------------------------------------------------------------------------


def reproject_layer_to_project_crs(
    layer, iface=None, project: "QgsProject | None" = None
) -> Tuple[bool, str]:
    """Reproject a layer to the current project CRS and add result to project.

    This is the single public entry point called by the dialog.

    Safety guarantees:
      - Original layer is NEVER modified.
      - Output filename always includes a UUID fragment.
      - The user is warned that the output is a temporary file.
      - Returns (False, error_message) on any failure — never raises.

    Args:
        layer:   QgsMapLayer to reproject.
        iface:   QGIS interface instance (used for message bar).
        project: QgsProject instance. Defaults to QgsProject.instance().

    Returns:
        (success: bool, message: str)
        On success, message is the display name of the added layer.
        On failure, message is a human-readable error description.
    """
    if project is None:
        project = QgsProject.instance()

    target_crs = project.crs()

    if not target_crs.isValid():
        msg = "Project CRS is invalid. Cannot reproject."
        QgsMessageLog.logMessage(msg, LOG_TAG, Qgis.Warning)
        _show_message(iface, msg, Qgis.Warning)
        return False, msg

    if not layer or not layer.isValid():
        msg = "Source layer is invalid. Cannot reproject."
        QgsMessageLog.logMessage(msg, LOG_TAG, Qgis.Warning)
        _show_message(iface, msg, Qgis.Warning)
        return False, msg

    layer_type = layer.type()

    if layer_type == LAYER_TYPE_VECTOR:
        output_path = _make_output_path(layer.name(), ".gpkg")
        success, result = _reproject_vector(layer, target_crs, output_path)
        if not success:
            _show_message(iface, f"Reprojection failed: {result}", Qgis.Critical)
            return False, result
        out_path = result

        new_layer = QgsVectorLayer(out_path, f"{layer.name()}_reprojected", "ogr")

    elif layer_type == LAYER_TYPE_RASTER:
        output_path = _make_output_path(layer.name(), ".tif")
        success, result = _reproject_raster(layer, target_crs, output_path)
        if not success:
            _show_message(iface, f"Reprojection failed: {result}", Qgis.Critical)
            return False, result
        out_path = result

        new_layer = QgsRasterLayer(out_path, f"{layer.name()}_reprojected")

    else:
        msg = (
            f"Layer '{layer.name()}' has type '{layer.type()}' which is not "
            "supported for reprojection. Only Vector and Raster layers are supported."
        )
        QgsMessageLog.logMessage(msg, LOG_TAG, Qgis.Warning)
        _show_message(iface, msg, Qgis.Warning)
        return False, msg

    if not new_layer.isValid():
        msg = (
            f"Output layer from reprojection of '{layer.name()}' is invalid. "
            f"Path: '{out_path}'. Check QGIS log for details."
        )
        QgsMessageLog.logMessage(msg, LOG_TAG, Qgis.Critical)
        _show_message(iface, msg, Qgis.Critical)
        return False, msg

    project.addMapLayer(new_layer)

    # Always warn user about temporary output
    _show_message(iface, TEMP_OUTPUT_WARNING, Qgis.Warning, duration=8)

    QgsMessageLog.logMessage(
        f"Reprojected layer '{layer.name()}' added as '{new_layer.name()}'.",
        LOG_TAG,
        Qgis.Info,
    )
    return True, new_layer.name()


# ---------------------------------------------------------------------------
# Message bar helper
# ---------------------------------------------------------------------------


def _show_message(iface, message: str, level, duration: int = 5) -> None:
    """Show a message in the QGIS message bar if iface is available.

    Args:
        iface:    QGIS interface instance, or None.
        message:  Message text.
        level:    Qgis.MessageLevel (Info, Warning, Critical, Success).
        duration: Seconds to show the bar. Default 5.
    """
    if iface is None:
        return
    try:
        iface.messageBar().pushMessage("CRS Mismatch Detector", message, level, duration)
    except Exception as exc:
        QgsMessageLog.logMessage(
            f"Could not show message bar: {exc}",
            LOG_TAG,
            Qgis.Warning,
        )
