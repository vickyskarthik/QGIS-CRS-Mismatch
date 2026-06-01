"""
CRS Mismatch Detector — Test Project Setup Script
==================================================
Run this inside the QGIS Python Console:
  Plugins → Python Console → paste and run

This script:
  1. Clears the current project.
  2. Sets the project CRS to EPSG:3857 (Web Mercator).
  3. Loads 4 layers with deliberately mixed CRS:
       - satellite_reference.tif   EPSG:3857  → MATCH
       - uav_example1.tif          EPSG:4326  → MISMATCH (raster)
       - survey_points_3857.gpkg   EPSG:3857  → MATCH
       - survey_points_4326.gpkg   EPSG:4326  → MISMATCH (vector)
  4. Opens the CRS Mismatch Detector dialog automatically.

Expected plugin result:
  2 mismatches detected out of 4 layers.
"""

import os
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE = '/home/mcw/Music/AIVE'
TEST_DATA = os.path.join(BASE, 'plugin', 'test_data')
ASSETS = os.path.join(BASE, 'multicoreware-aive-drone-a8e24dac859b', 'assets')

LAYERS = [
    # (path, name, provider, expected_crs, expect_mismatch)
    (
        os.path.join(ASSETS, 'satellite_reference.tif'),
        'satellite_reference [3857 ✓ MATCH]',
        'gdal',
        'EPSG:3857',
        False,
    ),
    (
        os.path.join(ASSETS, 'uav_example1.tif'),
        'uav_example1 [4326 ✗ MISMATCH]',
        'gdal',
        'EPSG:4326',
        True,
    ),
    (
        os.path.join(TEST_DATA, 'survey_points_3857.gpkg'),
        'survey_points [3857 ✓ MATCH]',
        'ogr',
        'EPSG:3857',
        False,
    ),
    (
        os.path.join(TEST_DATA, 'survey_points_4326.gpkg'),
        'survey_points [4326 ✗ MISMATCH]',
        'ogr',
        'EPSG:4326',
        True,
    ),
]

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

project = QgsProject.instance()
project.clear()

# Set project CRS to EPSG:3857
project_crs = QgsCoordinateReferenceSystem('EPSG:3857')
project.setCrs(project_crs)
print(f'Project CRS set to: {project_crs.authid()} — {project_crs.description()}')

# Load layers
loaded = 0
for path, name, provider, expected_crs, mismatch in LAYERS:
    if not os.path.exists(path):
        print(f'  SKIP (not found): {path}')
        continue

    if provider == 'gdal':
        layer = QgsRasterLayer(path, name)
    else:
        layer = QgsVectorLayer(path, name, provider)

    if not layer.isValid():
        print(f'  INVALID: {name}')
        continue

    actual_crs = layer.crs().authid()
    status = '✗ MISMATCH' if mismatch else '✓ MATCH'
    print(f'  Loaded: {name}  |  CRS: {actual_crs}  |  {status}')
    project.addMapLayer(layer)
    loaded += 1

print(f'\n{loaded} layers loaded. Project CRS: EPSG:3857')
print('Expected: 2 mismatches (uav_example1 + survey_points_4326)\n')

# ---------------------------------------------------------------------------
# Open the plugin dialog automatically
# ---------------------------------------------------------------------------

try:
    from crs_mismatch_detector.crs_mismatch_detector import CrsMismatchDetector  # noqa

    # Find the running plugin instance via iface
    plugin = iface.mainWindow().findChild(object, 'CrsMismatchDetectorToolBar')
    if plugin:
        print('Toolbar found — use the toolbar button or menu to open the dialog.')

    # Try to trigger via the plugin registry
    if 'crs_mismatch_detector' in [p.lower() for p in dir(iface)]:
        pass

    # Most reliable: use the menu action name
    for action in iface.pluginMenu().actions():
        if 'CRS Mismatch' in action.text():
            for sub in action.menu().actions() if action.menu() else []:
                if 'Check' in sub.text():
                    sub.trigger()
                    print('Plugin dialog opened automatically.')
                    break
            break
    else:
        print('To open the plugin: Plugins → CRS Mismatch Detector → Check CRS Mismatches')

except Exception as e:
    print(f'Auto-open skipped: {e}')
    print('To open: Plugins → CRS Mismatch Detector → Check CRS Mismatches')
