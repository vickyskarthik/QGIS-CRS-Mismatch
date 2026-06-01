# -*- coding: utf-8 -*-
"""
compat.py — QGIS version compatibility shims.

Centralises all version-specific API differences so the rest of the plugin
can use a single stable interface regardless of QGIS version.
"""

from qgis.core import Qgis, QgsMapLayer

# ---------------------------------------------------------------------------
# QGIS version integer helper
# ---------------------------------------------------------------------------

_QGIS_VERSION_INT: int = Qgis.QGIS_VERSION_INT


def qgis_version() -> int:
    """Return the QGIS version as an integer, e.g. 33400 for 3.34.0."""
    return _QGIS_VERSION_INT


# ---------------------------------------------------------------------------
# Layer type constants
# Normalised across the breaking change introduced in QGIS 3.x series.
# ---------------------------------------------------------------------------

# QgsMapLayerType was renamed to Qgis.LayerType in QGIS 3.36.
# Provide stable aliases for both old and new API.
try:
    # QGIS >= 3.36
    LAYER_TYPE_VECTOR = Qgis.LayerType.Vector
    LAYER_TYPE_RASTER = Qgis.LayerType.Raster
    LAYER_TYPE_PLUGIN = Qgis.LayerType.Plugin
    LAYER_TYPE_MESH = Qgis.LayerType.Mesh
    LAYER_TYPE_VECTOR_TILE = Qgis.LayerType.VectorTile
    LAYER_TYPE_ANNOTATION = Qgis.LayerType.Annotation
    LAYER_TYPE_POINT_CLOUD = Qgis.LayerType.PointCloud
except AttributeError:
    # QGIS < 3.36 — use QgsMapLayer.LayerType
    LAYER_TYPE_VECTOR = QgsMapLayer.VectorLayer
    LAYER_TYPE_RASTER = QgsMapLayer.RasterLayer
    LAYER_TYPE_PLUGIN = QgsMapLayer.PluginLayer
    LAYER_TYPE_MESH = getattr(QgsMapLayer, "MeshLayer", None)
    LAYER_TYPE_VECTOR_TILE = getattr(QgsMapLayer, "VectorTileLayer", None)
    LAYER_TYPE_ANNOTATION = getattr(QgsMapLayer, "AnnotationLayer", None)
    LAYER_TYPE_POINT_CLOUD = getattr(QgsMapLayer, "PointCloudLayer", None)


# ---------------------------------------------------------------------------
# Qgis severity level constants
# Provide stable aliases that work across versions.
# ---------------------------------------------------------------------------

try:
    MSG_INFO = Qgis.MessageLevel.Info
    MSG_WARNING = Qgis.MessageLevel.Warning
    MSG_CRITICAL = Qgis.MessageLevel.Critical
    MSG_SUCCESS = Qgis.MessageLevel.Success
except AttributeError:
    # QGIS < 3.20 used plain integer aliases
    MSG_INFO = Qgis.Info
    MSG_WARNING = Qgis.Warning
    MSG_CRITICAL = Qgis.Critical
    MSG_SUCCESS = getattr(Qgis, "Success", Qgis.Info)


def layer_type_name(layer) -> str:
    """Return a human-readable type string for a QgsMapLayer.

    Args:
        layer: QgsMapLayer instance.

    Returns:
        'Vector', 'Raster', 'Mesh', 'VectorTile', 'PointCloud',
        'Annotation', 'Plugin', or 'Other'.
    """
    lt = layer.type()
    if lt == LAYER_TYPE_VECTOR:
        return "Vector"
    if lt == LAYER_TYPE_RASTER:
        return "Raster"
    if LAYER_TYPE_MESH is not None and lt == LAYER_TYPE_MESH:
        return "Mesh"
    if LAYER_TYPE_VECTOR_TILE is not None and lt == LAYER_TYPE_VECTOR_TILE:
        return "VectorTile"
    if LAYER_TYPE_POINT_CLOUD is not None and lt == LAYER_TYPE_POINT_CLOUD:
        return "PointCloud"
    if LAYER_TYPE_ANNOTATION is not None and lt == LAYER_TYPE_ANNOTATION:
        return "Annotation"
    if lt == LAYER_TYPE_PLUGIN:
        return "Plugin"
    return "Other"


def is_reprojectable(layer) -> bool:
    """Return True if the layer type supports reprojection.

    Only Vector and Raster layers are reprojectable via Processing.

    Args:
        layer: QgsMapLayer instance.

    Returns:
        True if the layer is Vector or Raster.
    """
    lt = layer.type()
    return lt in (LAYER_TYPE_VECTOR, LAYER_TYPE_RASTER)
