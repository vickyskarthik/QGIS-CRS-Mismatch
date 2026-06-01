# -*- coding: utf-8 -*-
"""
crs_mismatch_detector.py — Main plugin lifecycle class.

Responsibilities:
  - Plugin load / unload.
  - Menu and toolbar registration.
  - QGIS project signal connection / disconnection.
  - Auto-scan on project open.
  - New-layer-added CRS warning.
  - Opening the CRS Mismatch Dialog.
"""

from __future__ import annotations

import os

from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsSettings
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

LOG_TAG = "CRS Mismatch Detector"
SETTINGS_KEY_AUTO_CHECK = "crs_mismatch_detector/auto_check_on_open"


class CrsMismatchDetector:
    """QGIS Plugin — CRS Mismatch Detector.

    Manages the plugin lifecycle: loading, unloading, UI registration,
    and QGIS project signal connections.
    """

    def __init__(self, iface):
        """Initialise the plugin.

        Args:
            iface: QgisInterface provided by QGIS plugin loader.
        """
        self.iface = iface
        self.plugin_dir: str = os.path.dirname(__file__)

        self._action: QAction | None = None
        self._toolbar = None
        self._dialog = None

        # Track connected signals so we can disconnect safely in unload()
        self._signals_connected: bool = False

    # ------------------------------------------------------------------
    # Plugin lifecycle
    # ------------------------------------------------------------------

    def initGui(self) -> None:
        """Set up the plugin UI: menu entry, toolbar button, and signals."""
        icon_path = os.path.join(self.plugin_dir, "icons", "icon.png")
        icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()

        self._action = QAction(icon, "Check CRS Mismatches", self.iface.mainWindow())
        self._action.setToolTip("Scan project layers for CRS mismatches")
        self._action.triggered.connect(self.run)

        # Menu
        self.iface.addPluginToMenu("CRS Mismatch Detector", self._action)

        # Toolbar
        self._toolbar = self.iface.addToolBar("CRS Mismatch Detector")
        self._toolbar.setObjectName("CrsMismatchDetectorToolBar")
        self._toolbar.addAction(self._action)

        # Connect project signals
        self._connect_signals()

        QgsMessageLog.logMessage("CRS Mismatch Detector loaded.", LOG_TAG, Qgis.Info)

    def unload(self) -> None:
        """Remove the plugin UI and disconnect all signals."""
        # Disconnect signals first
        self._disconnect_signals()

        # Close and delete the dialog if open
        if self._dialog is not None:
            try:
                self._dialog.close()
            except Exception:
                pass
            try:
                self._dialog.deleteLater()
            except Exception:
                pass
            self._dialog = None

        # Remove menu entry
        if self._action is not None:
            self.iface.removePluginMenu("CRS Mismatch Detector", self._action)

        # Remove toolbar
        if self._toolbar is not None:
            self._toolbar.clear()
            self.iface.mainWindow().removeToolBar(self._toolbar)
            self._toolbar.deleteLater()
            self._toolbar = None

        if self._action is not None:
            self._action.deleteLater()
            self._action = None

        QgsMessageLog.logMessage("CRS Mismatch Detector unloaded.", LOG_TAG, Qgis.Info)

    # ------------------------------------------------------------------
    # Dialog
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Open the CRS Mismatch Detector dialog."""
        from .crs_mismatch_dialog import CrsMismatchDialog

        if self._dialog is None:
            self._dialog = CrsMismatchDialog(self.iface, parent=self.iface.mainWindow())

        self._dialog.refresh()
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()

    # ------------------------------------------------------------------
    # Signal management
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """Connect to QGIS project signals for auto-scan and new-layer warning."""
        if self._signals_connected:
            return

        QgsProject.instance().readProject.connect(self._on_project_read)
        QgsProject.instance().layerWasAdded.connect(self._on_layer_added)

        self._signals_connected = True
        QgsMessageLog.logMessage("Project signals connected.", LOG_TAG, Qgis.Info)

    def _disconnect_signals(self) -> None:
        """Safely disconnect project signals."""
        if not self._signals_connected:
            return

        try:
            QgsProject.instance().readProject.disconnect(self._on_project_read)
        except (TypeError, RuntimeError):
            pass

        try:
            QgsProject.instance().layerWasAdded.disconnect(self._on_layer_added)
        except (TypeError, RuntimeError):
            pass

        self._signals_connected = False
        QgsMessageLog.logMessage("Project signals disconnected.", LOG_TAG, Qgis.Info)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_project_read(self, *args) -> None:
        """Handler for QgsProject.readProject signal.

        Runs an auto-scan and shows a message-bar warning when mismatches
        exist — but only if the auto-check setting is enabled.
        """
        if not self._auto_check_enabled():
            return

        try:
            from .crs_checker import mismatch_count

            count = mismatch_count()
            if count > 0:
                plural = "layer" if count == 1 else "layers"
                self._show_mismatch_warning(
                    f"{count} {plural} with CRS mismatches found in this project.",
                    duration=10,
                )
                QgsMessageLog.logMessage(
                    f"Auto-scan on project open: {count} mismatch(es) found.",
                    LOG_TAG,
                    Qgis.Warning,
                )
        except Exception as exc:
            QgsMessageLog.logMessage(
                f"Auto-scan error: {exc}", LOG_TAG, Qgis.Critical
            )

    def _on_layer_added(self, layer) -> None:
        """Handler for QgsProject.layerWasAdded signal.

        Checks whether the newly added layer has a CRS mismatch with the
        project CRS and shows a warning if so.
        """
        try:
            from .crs_checker import _compute_mismatch

            project_crs = QgsProject.instance().crs()
            if layer is None or not layer.isValid():
                return

            if _compute_mismatch(layer.crs(), project_crs):
                self._show_mismatch_warning(
                    f"Layer '{layer.name()}' has a CRS that differs from the "
                    "project CRS. Click Details to review.",
                    duration=8,
                    with_details=True,
                )
                QgsMessageLog.logMessage(
                    f"New mismatched layer added: '{layer.name()}'.",
                    LOG_TAG,
                    Qgis.Warning,
                )
        except Exception as exc:
            QgsMessageLog.logMessage(
                f"Layer-added check error: {exc}", LOG_TAG, Qgis.Critical
            )

    # ------------------------------------------------------------------
    # Message bar helpers
    # ------------------------------------------------------------------

    def _show_mismatch_warning(
        self, message: str, duration: int = 8, with_details: bool = False
    ) -> None:
        """Push a warning to the QGIS message bar.

        Args:
            message:      Text to display.
            duration:     Seconds before the bar auto-dismisses.
            with_details: If True, add a "Details" button that opens the dialog.
        """
        try:
            from qgis.PyQt.QtWidgets import QPushButton

            bar = self.iface.messageBar()
            widget = bar.createMessage("CRS Mismatch Detector", message)

            if with_details:
                btn = QPushButton("Details")
                btn.pressed.connect(self.run)
                widget.layout().addWidget(btn)

            bar.pushWidget(widget, Qgis.Warning, duration)

        except Exception as exc:
            QgsMessageLog.logMessage(
                f"Could not show message bar warning: {exc}", LOG_TAG, Qgis.Warning
            )

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _auto_check_enabled(self) -> bool:
        """Return True if auto-check on project open is enabled.

        Uses QgsSettings (not QSettings) as required by plugin rules.

        Returns:
            True if auto-check is enabled (default: True).
        """
        try:
            settings = QgsSettings()
            return bool(settings.value(SETTINGS_KEY_AUTO_CHECK, True, type=bool))
        except Exception:
            return True
