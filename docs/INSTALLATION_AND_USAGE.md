# Installation and Usage Guide — CRS Mismatch Detector

## 1. What This Plugin Does

CRS Mismatch Detector checks whether the layers in your QGIS project use the same CRS as the project CRS.

If a layer uses a different CRS, the plugin marks it as a mismatch.

You can create a corrected reprojected copy of that layer.

**The original layer is not changed.**

---

## 2. Why This Matters

QGIS can display layers correctly even when they have different CRS values. This is because QGIS uses on-the-fly reprojection for display.

However, CRS differences can affect:

- Distance measurement
- Area calculation
- Buffering
- Overlay and intersection
- Spatial joins
- Raster processing
- Data export

This plugin helps you find mismatches before analysis.

---

## 3. System Requirements

| Requirement | Minimum |
|---|---|
| QGIS | 3.10 |
| Python | 3.6 |
| External dependencies | None |

---

## 4. Installation from QGIS Plugin Manager

1. Open QGIS.
2. Go to: `Plugins → Manage and Install Plugins`
3. Search: `CRS Mismatch Detector`
4. Click: **Install Plugin**
5. Open it from: `Plugins → CRS Mismatch Detector → Check CRS Mismatches`

---

## 5. Installation from ZIP

Use this for testing pre-release builds.

1. Open QGIS.
2. Go to: `Plugins → Manage and Install Plugins → Install from ZIP`
3. Select the plugin ZIP file.
4. Click **Install Plugin**.
5. Enable the plugin in the installed plugins list.

---

## 6. Manual Installation (developers)

```bash
cp -r crs_mismatch_detector \
  ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

Then restart QGIS or use the Plugin Reloader plugin.

---

## 7. Opening the Plugin

- Menu: `Plugins → CRS Mismatch Detector → Check CRS Mismatches`
- Toolbar: Click the globe-with-warning icon

---

## 8. Main Dialog

The dialog shows a results table with the following columns:

| Column | Meaning |
|---|---|
| Layer Name | Name of the layer in the QGIS project |
| Type | Vector, Raster, Mesh, etc. |
| Layer CRS | CRS assigned to the layer (full text in tooltip) |
| Project CRS | Current project CRS (full text in tooltip) |
| Mismatch Type | Description of the CRS difference |
| Status | **Match** (green) or **Mismatch** (red) |
| Action | Reproject button for mismatched layers |

---

## 9. Scanning Layers

1. Open your QGIS project.
2. Open the plugin dialog.
3. Click **Refresh**.

The plugin scans all loaded layers and updates the table.

---

## 10. Show All Layers

By default, only mismatched layers are shown.

To see all layers: enable the **Show all layers** checkbox.  
To show only mismatches: disable it.

The setting is saved automatically.

---

## 11. Reprojecting One Layer

1. Find a mismatched layer in the table.
2. Click the **Reproject** button in the Action column.
3. A new layer named `<LayerName>_reprojected` is added to the project.

The original layer remains unchanged.

---

## 12. Reprojecting All Mismatched Layers

1. Click **Reproject All Mismatched Layers**.
2. Confirm the dialog that lists how many layers will be processed.
3. Wait for the progress dialog to complete.

Reprojected copies are added to the project for all mismatched reprojectable layers.

---

## 13. Temporary Output Warning

After every reprojection you will see this message:

> **The reprojected layer was added as a temporary file. Export it permanently if you want to keep it.**

Temporary files may be deleted when QGIS closes or when the operating system clears temporary files.

**To save a reprojected layer permanently:**

For vector layers:
1. Right-click the reprojected layer in the Layers panel.
2. Select: `Export → Save Features As…`
3. Choose a permanent folder and format.

For raster layers:
1. Right-click the reprojected layer.
2. Select: `Export → Save As…`
3. Choose a permanent folder and format.

---

## 14. Auto-Check on Project Open

The plugin can automatically check for CRS mismatches whenever a QGIS project is opened.

To enable or disable:

1. Open the plugin dialog.
2. Toggle: **Auto-check when project opens**

The setting is saved in your QGIS profile and persists across restarts.

---

## 15. New Layer Warning

When you add a new layer whose CRS differs from the project CRS, the plugin shows a warning in the QGIS message bar.

Click **Details** to open the plugin dialog and review the mismatch.

---

## 16. Copying CRS Information

Right-click any row in the table to access:

- **Copy Layer CRS** — copies the full CRS string to the clipboard.
- **Copy Project CRS** — copies the project CRS string to the clipboard.

---

## 17. Troubleshooting

### Plugin Does Not Appear in Menu

1. Go to: `Plugins → Manage and Install Plugins`
2. Confirm the plugin is enabled (checkbox ticked).
3. Restart QGIS.
4. If the problem persists, reinstall the plugin.

### Reproject Button Is Greyed Out or Missing

The layer type does not support reprojection via Processing.  
Only Vector and Raster layers can be reprojected. Mesh, VectorTile, PointCloud, and Annotation layers show "Not supported" in the Action column.

### Reproject Fails

Possible causes:
- Project CRS is not set or invalid.
- Layer was removed from the project after the last scan (click Refresh).
- QGIS Processing framework is unavailable.
- Disk space is insufficient for the output file.
- The source file is on a read-only or network drive with a broken connection.

Check: `View → Panels → Log Messages → CRS Mismatch Detector`

### Reprojected Layer Disappeared

The layer was stored as a temporary file. Export it permanently.  
See section 13 above.

### Map Looks Correct but Plugin Shows Mismatch

This is expected behaviour. QGIS uses on-the-fly reprojection to display layers correctly regardless of their CRS. The plugin reports the internal CRS difference, which can affect analysis even if the display looks correct.

### Plugin Crashes on Reload

If you use Plugin Reloader:
1. Close the plugin dialog first.
2. Then reload.

If crashes persist, check the QGIS Python error log.

---

## 18. Recommended Workflow Before Analysis

1. Set the correct project CRS: `Project → Properties → CRS`.
2. Open CRS Mismatch Detector.
3. Click **Refresh**.
4. Review mismatched layers.
5. Click **Reproject** for each layer that needs correction.
6. Export reprojected outputs to permanent files.
7. Remove or replace original mismatched layers in the project.
8. Use the permanent corrected layers for your analysis.
