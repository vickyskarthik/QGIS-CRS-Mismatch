# -*- coding: utf-8 -*-
"""
crs_mismatch_dialog.py — CRS Mismatch Detector dialog.

Responsibilities:
  - Load UI from crs_mismatch_dialog_base.ui.
  - Populate the results table.
  - Provide per-row Reproject buttons keyed on stable layer ID.
  - Provide Reproject All with confirmation and progress dialog.
  - Persist auto-check setting via QgsSettings.
  - Copy CRS context menu.
  - Show All / mismatches-only toggle.
"""

from __future__ import annotations

import os
from typing import List

from qgis.core import Qgis, QgsMessageLog, QgsSettings
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QApplication,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTableWidgetItem,
)

from .crs_checker import LayerCrsInfo, get_layer_by_id, get_mismatches, scan_all_layers
from .utils import reproject_layer_to_project_crs

LOG_TAG = "CRS Mismatch Detector"
SETTINGS_KEY_AUTO_CHECK = "crs_mismatch_detector/auto_check_on_open"
SETTINGS_KEY_SHOW_ALL = "crs_mismatch_detector/show_all_layers"

# Column indices — defined as constants to avoid magic numbers
COL_NAME = 0
COL_TYPE = 1
COL_LAYER_CRS = 2
COL_PROJECT_CRS = 3
COL_MISMATCH_TYPE = 4
COL_STATUS = 5
COL_ACTION = 6

# Colours for status cells
COLOR_MISMATCH_BG = QColor("#fce8e8")
COLOR_MISMATCH_FG = QColor("#c0392b")
COLOR_MATCH_BG = QColor("#e8f5e9")
COLOR_MATCH_FG = QColor("#2e7d32")

# Max visible characters for CRS display strings in table cells
CRS_MAX_DISPLAY = 45

# Load the UI form class
_FORM_CLASS, _BASE_CLASS = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "crs_mismatch_dialog_base.ui")
)


class CrsMismatchDialog(_BASE_CLASS, _FORM_CLASS):
    """Main CRS Mismatch Detector dialog window."""

    def __init__(self, iface, parent=None):
        """Initialise the dialog.

        Args:
            iface:  QgisInterface instance used for reprojection helpers.
            parent: Qt parent widget (should be the QGIS main window).
        """
        super().__init__(parent)
        self.setupUi(self)

        self.iface = iface
        self._results: List[LayerCrsInfo] = []

        # ------------------------------------------------------------------
        # Table setup
        # ------------------------------------------------------------------
        self.tableWidget.setColumnCount(7)
        self.tableWidget.setHorizontalHeaderLabels(
            ["Layer Name", "Type", "Layer CRS", "Project CRS",
             "Mismatch Type", "Status", "Action"]
        )
        header = self.tableWidget.horizontalHeader()
        # Stretch columns that contain long strings
        try:
            from qgis.PyQt.QtWidgets import QHeaderView
            header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(COL_TYPE, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(COL_LAYER_CRS, QHeaderView.Stretch)
            header.setSectionResizeMode(COL_PROJECT_CRS, QHeaderView.Stretch)
            header.setSectionResizeMode(COL_MISMATCH_TYPE, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(COL_ACTION, QHeaderView.ResizeToContents)
        except Exception:
            pass

        # ------------------------------------------------------------------
        # Restore persisted settings
        # ------------------------------------------------------------------
        settings = QgsSettings()
        auto_check = bool(settings.value(SETTINGS_KEY_AUTO_CHECK, True, type=bool))
        show_all = bool(settings.value(SETTINGS_KEY_SHOW_ALL, False, type=bool))

        self.checkBoxAutoCheck.setChecked(auto_check)
        self.checkBoxShowAll.setChecked(show_all)

        # ------------------------------------------------------------------
        # Connect signals
        # ------------------------------------------------------------------
        self.btnRefresh.clicked.connect(self.refresh)
        self.btnReprojectAll.clicked.connect(self._on_reproject_all)
        self.btnClose.clicked.connect(self.close)
        self.checkBoxShowAll.stateChanged.connect(self._on_show_all_changed)
        self.checkBoxAutoCheck.stateChanged.connect(self._on_auto_check_changed)
        self.tableWidget.customContextMenuRequested.connect(self._on_context_menu)

        # Window flags: keep on top of QGIS main window but not system-modal
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Rescan all project layers and repopulate the table."""
        QgsMessageLog.logMessage("Dialog: refreshing CRS scan.", LOG_TAG, Qgis.Info)
        self._results = scan_all_layers()
        self._populate_table()

    # ------------------------------------------------------------------
    # Table population
    # ------------------------------------------------------------------

    def _populate_table(self) -> None:
        """Populate the results table from self._results.

        Respects the Show All checkbox — when unchecked, only mismatched
        layers are displayed.
        """
        show_all = self.checkBoxShowAll.isChecked()
        rows = self._results if show_all else get_mismatches(self._results)

        # Disable sorting during population to avoid row-index shifts
        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.setRowCount(0)

        mismatch_count = sum(1 for r in self._results if r.is_mismatch)
        total = len(self._results)

        for row_data in rows:
            row = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row)
            self._fill_row(row, row_data)

        # Re-enable sorting
        self.tableWidget.setSortingEnabled(True)
        self.tableWidget.resizeColumnsToContents()

        # Update summary label
        if mismatch_count == 0:
            summary = f"✅  No CRS mismatches found in {total} layer(s)."
        else:
            plural = "layer" if mismatch_count == 1 else "layers"
            summary = (
                f"⚠️  {mismatch_count} mismatched {plural} found out of {total} total."
            )
        self.labelSummary.setText(summary)

        # Enable/disable Reproject All
        self.btnReprojectAll.setEnabled(mismatch_count > 0)

    def _fill_row(self, row: int, data: LayerCrsInfo) -> None:
        """Fill one table row with data from a LayerCrsInfo.

        The stable layer_id is stored as Qt.UserRole in every cell of the
        row so that reprojection always targets the correct layer regardless
        of sorting or row-index changes.

        Args:
            row:  Table row index.
            data: LayerCrsInfo for this row.
        """
        layer_id = data.layer_id

        def _make_item(text: str, display_text: str | None = None) -> QTableWidgetItem:
            item = QTableWidgetItem(display_text if display_text is not None else text)
            item.setData(Qt.UserRole, layer_id)
            item.setToolTip(text)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            return item

        def _truncate(s: str, n: int = CRS_MAX_DISPLAY) -> str:
            return s if len(s) <= n else s[:n] + "…"

        # Layer Name
        name_item = _make_item(data.layer_name)
        self.tableWidget.setItem(row, COL_NAME, name_item)

        # Type
        self.tableWidget.setItem(row, COL_TYPE, _make_item(data.layer_type))

        # Layer CRS (truncated in cell, full text in tooltip)
        layer_crs_item = _make_item(data.layer_crs_str, _truncate(data.layer_crs_str))
        self.tableWidget.setItem(row, COL_LAYER_CRS, layer_crs_item)

        # Project CRS
        proj_crs_item = _make_item(data.project_crs_str, _truncate(data.project_crs_str))
        self.tableWidget.setItem(row, COL_PROJECT_CRS, proj_crs_item)

        # Mismatch Type
        self.tableWidget.setItem(row, COL_MISMATCH_TYPE, _make_item(data.mismatch_type))

        # Status — coloured
        status_item = _make_item(data.status)
        if data.is_mismatch:
            status_item.setBackground(COLOR_MISMATCH_BG)
            status_item.setForeground(COLOR_MISMATCH_FG)
        else:
            status_item.setBackground(COLOR_MATCH_BG)
            status_item.setForeground(COLOR_MATCH_FG)
        self.tableWidget.setItem(row, COL_STATUS, status_item)

        # Action column — Reproject button (only for mismatched reprojectable layers)
        if data.is_mismatch and data.reprojectable:
            btn = QPushButton("Reproject")
            btn.setToolTip(f"Reproject '{data.layer_name}' to the project CRS")
            # Use a closure that captures the stable layer_id, not the row index
            btn.clicked.connect(lambda checked, lid=layer_id: self._reproject_by_layer_id(lid))
            self.tableWidget.setCellWidget(row, COL_ACTION, btn)
        elif data.is_mismatch and not data.reprojectable:
            unsupported_item = QTableWidgetItem("Not supported")
            unsupported_item.setData(Qt.UserRole, layer_id)
            unsupported_item.setToolTip(
                f"Layer type '{data.layer_type}' does not support reprojection."
            )
            unsupported_item.setFlags(Qt.ItemIsEnabled)
            self.tableWidget.setItem(row, COL_ACTION, unsupported_item)

    # ------------------------------------------------------------------
    # Reprojection
    # ------------------------------------------------------------------

    def _reproject_by_layer_id(self, layer_id: str) -> None:
        """Reproject the layer identified by layer_id.

        Uses the stable QGIS layer ID — never a row index.

        Args:
            layer_id: The QgsMapLayer.id() string stored in the cell's UserRole.
        """
        layer = get_layer_by_id(layer_id)
        if layer is None:
            QMessageBox.warning(
                self,
                "Layer Not Found",
                f"The layer could not be found (ID: {layer_id}).\n"
                "It may have been removed since the last scan. Click Refresh and try again.",
            )
            QgsMessageLog.logMessage(
                f"Reproject failed: layer '{layer_id}' not found.",
                LOG_TAG,
                Qgis.Warning,
            )
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            success, message = reproject_layer_to_project_crs(layer, self.iface)
        finally:
            QApplication.restoreOverrideCursor()

        if success:
            self.refresh()
        else:
            QMessageBox.critical(
                self,
                "Reprojection Failed",
                f"Could not reproject layer '{layer.name()}'.\n\nDetails: {message}",
            )

    def _on_reproject_all(self) -> None:
        """Handle the Reproject All button."""
        mismatches = get_mismatches(self._results)
        reprojectable = [m for m in mismatches if m.reprojectable]

        if not reprojectable:
            QMessageBox.information(
                self,
                "Nothing to Reproject",
                "There are no reprojectable mismatched layers in the current scan.\n"
                "Click Refresh to update the results.",
            )
            return

        count = len(reprojectable)
        plural = "layer" if count == 1 else "layers"

        answer = QMessageBox.question(
            self,
            "Reproject All Mismatched Layers",
            f"This will create reprojected copies of {count} mismatched {plural}.\n\n"
            "• Original layers will NOT be modified.\n"
            "• Output files are temporary — export them permanently to keep them.\n\n"
            "Proceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            QgsMessageLog.logMessage("Reproject All cancelled by user.", LOG_TAG, Qgis.Info)
            return

        progress = QProgressDialog(
            "Reprojecting layers…", "Cancel", 0, count, self
        )
        progress.setWindowTitle("Reproject All")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        failed = []
        for i, info in enumerate(reprojectable):
            if progress.wasCanceled():
                QgsMessageLog.logMessage(
                    f"Reproject All cancelled after {i} of {count}.",
                    LOG_TAG,
                    Qgis.Info,
                )
                break

            progress.setLabelText(f"Reprojecting '{info.layer_name}' ({i + 1}/{count})…")
            QApplication.processEvents()

            layer = get_layer_by_id(info.layer_id)
            if layer is None:
                failed.append(f"'{info.layer_name}' — layer not found (removed?)")
                progress.setValue(i + 1)
                continue

            success, message = reproject_layer_to_project_crs(layer, self.iface)
            if not success:
                failed.append(f"'{info.layer_name}' — {message}")

            progress.setValue(i + 1)

        progress.close()
        self.refresh()

        if failed:
            error_list = "\n".join(f"  • {f}" for f in failed)
            QMessageBox.warning(
                self,
                "Reproject All — Some Failures",
                f"The following layers could not be reprojected:\n\n{error_list}\n\n"
                "Check the QGIS log (View → Panels → Log Messages) for details.",
            )

    # ------------------------------------------------------------------
    # Context menu — copy CRS strings
    # ------------------------------------------------------------------

    def _on_context_menu(self, pos) -> None:
        """Show a context menu allowing the user to copy CRS strings.

        Args:
            pos: QPoint position of the right-click in the table viewport.
        """
        item = self.tableWidget.itemAt(pos)
        if item is None:
            return

        row = item.row()

        def _cell_text(col: int) -> str:
            cell_item = self.tableWidget.item(row, col)
            return cell_item.toolTip() if cell_item else ""

        layer_crs_text = _cell_text(COL_LAYER_CRS)
        project_crs_text = _cell_text(COL_PROJECT_CRS)

        menu = QMenu(self)

        if layer_crs_text:
            act_layer_crs = menu.addAction(f"Copy Layer CRS: {layer_crs_text[:60]}")
            act_layer_crs.triggered.connect(
                lambda: QApplication.clipboard().setText(layer_crs_text)
            )

        if project_crs_text:
            act_proj_crs = menu.addAction(f"Copy Project CRS: {project_crs_text[:60]}")
            act_proj_crs.triggered.connect(
                lambda: QApplication.clipboard().setText(project_crs_text)
            )

        if not menu.isEmpty():
            menu.exec_(self.tableWidget.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    # Settings handlers
    # ------------------------------------------------------------------

    def _on_show_all_changed(self, state: int) -> None:
        """Respond to Show All checkbox change and repopulate table.

        Args:
            state: Qt checkbox state integer.
        """
        show_all = state == Qt.Checked
        settings = QgsSettings()
        settings.setValue(SETTINGS_KEY_SHOW_ALL, show_all)
        self._populate_table()

    def _on_auto_check_changed(self, state: int) -> None:
        """Persist the auto-check setting when the checkbox is toggled.

        Args:
            state: Qt checkbox state integer.
        """
        enabled = state == Qt.Checked
        settings = QgsSettings()
        settings.setValue(SETTINGS_KEY_AUTO_CHECK, enabled)
        QgsMessageLog.logMessage(
            f"Auto-check on project open set to: {enabled}.", LOG_TAG, Qgis.Info
        )
