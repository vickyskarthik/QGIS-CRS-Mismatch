# -*- coding: utf-8 -*-
"""
crs_checker.py — CRS mismatch detection business logic.

Responsibilities:
  - Robust CRS comparison (NOT only authid()).
  - Layer scanning.
  - LayerCrsInfo data model.
  - Mismatch severity categorisation.

This module must NOT import or depend on iface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from qgis.core import QgsMapLayer, QgsProject

from .compat import LAYER_TYPE_PLUGIN, is_reprojectable, layer_type_name

# ---------------------------------------------------------------------------
# Log tag used throughout this module
# ---------------------------------------------------------------------------
LOG_TAG = "CRS Mismatch Detector"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class LayerCrsInfo:
    """Snapshot of CRS relationship between a layer and the project.

    Attributes:
        layer_id:       Stable QGIS layer ID (used for all actions).
        layer_name:     Human-readable layer name.
        layer_type:     Human-readable layer type string.
        layer_crs_str:  Display string for the layer CRS.
        project_crs_str: Display string for the project CRS.
        is_mismatch:    True when a CRS difference is detected.
        mismatch_type:  Short descriptor of the mismatch kind.
        status:         'Match' or 'Mismatch'.
        reprojectable:  True when the layer type supports reprojection.
    """

    layer_id: str
    layer_name: str
    layer_type: str
    layer_crs_str: str
    project_crs_str: str
    is_mismatch: bool
    mismatch_type: str
    status: str
    reprojectable: bool

    # Not serialised — live reference used internally (may become None if layer removed)
    _layer_ref: Optional[object] = field(default=None, repr=False, compare=False)


# ---------------------------------------------------------------------------
# Core CRS comparison
# ---------------------------------------------------------------------------


def _compute_mismatch(layer_crs, project_crs) -> bool:
    """Robustly compare two QgsCoordinateReferenceSystem instances.

    Rules (in priority order):
      1. If either CRS is invalid → False (cannot determine mismatch safely).
      2. If the CRS objects are equal by Qt operator== → False.
      3. If both authids are non-empty and equal → False.
      4. If both authids are empty → compare toProj() strings.
      5. Otherwise → True (mismatched).

    Args:
        layer_crs:   QgsCoordinateReferenceSystem of the layer.
        project_crs: QgsCoordinateReferenceSystem of the project.

    Returns:
        True if a mismatch is detected.
    """
    if not layer_crs.isValid() or not project_crs.isValid():
        return False

    # Qt operator== checks internal WKT and authority, not just authid
    if layer_crs == project_crs:
        return False

    l_id = layer_crs.authid()
    p_id = project_crs.authid()

    if l_id and p_id and l_id == p_id:
        return False

    # Both have no authority id — fall back to PROJ string comparison
    if not l_id and not p_id:
        return layer_crs.toProj() != project_crs.toProj()

    return True


def _mismatch_type(layer_crs, project_crs) -> str:
    """Return a short descriptor categorising the mismatch.

    Args:
        layer_crs:   QgsCoordinateReferenceSystem of the layer.
        project_crs: QgsCoordinateReferenceSystem of the project.

    Returns:
        One of:
          'No mismatch'
          'Invalid layer CRS'
          'Invalid project CRS'
          'Both CRS invalid'
          'Different authid'
          'Same authid, different definition'
          'Custom CRS difference'
    """
    if not layer_crs.isValid() and not project_crs.isValid():
        return "Both CRS invalid"
    if not layer_crs.isValid():
        return "Invalid layer CRS"
    if not project_crs.isValid():
        return "Invalid project CRS"

    l_id = layer_crs.authid()
    p_id = project_crs.authid()

    if l_id and p_id:
        if l_id != p_id:
            return "Different authid"
        # Same authid but operator== returned False — internal definition differs
        return "Same authid, different definition"

    if not l_id and not p_id:
        return "Custom CRS difference"

    # One has an authid, the other does not
    return "Different authid"


def _crs_display_string(crs) -> str:
    """Return a descriptive display string for a CRS.

    Includes authid when available, falls back to description, then 'Unknown'.

    Args:
        crs: QgsCoordinateReferenceSystem instance.

    Returns:
        Display string suitable for showing in the UI.
    """
    if not crs.isValid():
        return "Invalid CRS"

    auth_id = crs.authid()
    description = crs.description()

    if auth_id and description:
        return f"{auth_id} — {description}"
    if auth_id:
        return auth_id
    if description:
        return description

    proj_str = crs.toProj()
    if proj_str:
        # Truncate very long PROJ strings
        return proj_str[:80] + ("…" if len(proj_str) > 80 else "")

    return "Unknown CRS"


# ---------------------------------------------------------------------------
# Layer scanning
# ---------------------------------------------------------------------------


def _should_skip_layer(layer) -> bool:
    """Return True if the layer should be excluded from scanning.

    Plugin layers and invalid layers are skipped.

    Args:
        layer: QgsMapLayer instance.

    Returns:
        True if the layer must be skipped.
    """
    if layer is None:
        return True
    if not layer.isValid():
        return True
    if layer.type() == LAYER_TYPE_PLUGIN:
        return True
    return False


def scan_all_layers(project: Optional[QgsProject] = None) -> List[LayerCrsInfo]:
    """Scan every eligible layer in the QGIS project and return CRS info.

    Args:
        project: QgsProject instance to scan.
                 Defaults to QgsProject.instance() if None.

    Returns:
        List of LayerCrsInfo — one entry per scanned layer.
        The list is sorted: mismatches first, then by layer name.
    """
    if project is None:
        project = QgsProject.instance()

    project_crs = project.crs()
    project_crs_str = _crs_display_string(project_crs)

    results: List[LayerCrsInfo] = []

    for layer in project.mapLayers().values():
        if _should_skip_layer(layer):
            _log_skipped(layer)
            continue

        layer_crs = layer.crs()
        mismatch = _compute_mismatch(layer_crs, project_crs)
        mtype = _mismatch_type(layer_crs, project_crs) if mismatch else "No mismatch"

        info = LayerCrsInfo(
            layer_id=layer.id(),
            layer_name=layer.name(),
            layer_type=layer_type_name(layer),
            layer_crs_str=_crs_display_string(layer_crs),
            project_crs_str=project_crs_str,
            is_mismatch=mismatch,
            mismatch_type=mtype,
            status="Mismatch" if mismatch else "Match",
            reprojectable=is_reprojectable(layer),
            _layer_ref=layer,
        )
        results.append(info)

    # Sort: mismatches first, then alphabetically by layer name
    results.sort(key=lambda r: (not r.is_mismatch, r.layer_name.lower()))
    return results


def get_mismatches(results: List[LayerCrsInfo]) -> List[LayerCrsInfo]:
    """Filter a scan result list to only mismatched layers.

    Args:
        results: List returned by scan_all_layers().

    Returns:
        Subset containing only entries where is_mismatch is True.
    """
    return [r for r in results if r.is_mismatch]


def get_layer_by_id(layer_id: str, project: Optional[QgsProject] = None) -> Optional[QgsMapLayer]:
    """Look up a live QgsMapLayer by its stable ID.

    Args:
        layer_id: The layer ID string returned by QgsMapLayer.id().
        project:  QgsProject to search. Defaults to QgsProject.instance().

    Returns:
        The QgsMapLayer if found and valid, otherwise None.
    """
    if project is None:
        project = QgsProject.instance()
    layer = project.mapLayer(layer_id)
    if layer is None or not layer.isValid():
        return None
    return layer


def mismatch_count(project: Optional[QgsProject] = None) -> int:
    """Quick count of mismatched layers without building full LayerCrsInfo objects.

    Useful for notification badges and auto-scan message bars.

    Args:
        project: QgsProject to scan. Defaults to QgsProject.instance().

    Returns:
        Number of layers with a CRS mismatch.
    """
    if project is None:
        project = QgsProject.instance()
    project_crs = project.crs()
    count = 0
    for layer in project.mapLayers().values():
        if _should_skip_layer(layer):
            continue
        if _compute_mismatch(layer.crs(), project_crs):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Internal logging helpers
# ---------------------------------------------------------------------------


def _log_skipped(layer) -> None:
    """Log a message when a layer is skipped during scanning."""
    try:
        from qgis.core import Qgis, QgsMessageLog

        name = layer.name() if layer and hasattr(layer, "name") else "<unknown>"
        QgsMessageLog.logMessage(
            f"Skipping layer '{name}' during CRS scan (invalid or plugin layer).",
            LOG_TAG,
            Qgis.Info,
        )
    except Exception:
        pass
