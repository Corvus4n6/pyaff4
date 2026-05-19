import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QGroupBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from pyaff4.gui.workers import VerifyWorker


PASS_COLOR = QColor("#c8e6c9")
FAIL_COLOR = QColor("#ffcdd2")

_SUMMARY_PASS_STYLE = (
    "color: white; background-color: #2e7d32; "
    "font-weight: bold; font-size: 14px; padding: 6px; border-radius: 4px;"
)
_SUMMARY_FAIL_STYLE = (
    "color: white; background-color: #b71c1c; "
    "font-weight: bold; font-size: 14px; padding: 6px; border-radius: 4px;"
)
_SUMMARY_NEUTRAL_STYLE = ""


class VerifyTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._fail_count = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # File picker
        file_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("AFF4 container path...")
        self.path_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(self.path_edit)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        # Controls
        ctrl_row = QHBoxLayout()
        self.start_btn = QPushButton("Start Verification")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        ctrl_row.addWidget(self.start_btn)
        ctrl_row.addWidget(self.cancel_btn)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # Progress
        prog_group = QGroupBox("Progress")
        prog_layout = QVBoxLayout(prog_group)
        image_row = QHBoxLayout()
        image_row.addWidget(QLabel("Image:"))
        self.current_image_label = QLabel("-")
        self.current_image_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        image_row.addWidget(self.current_image_label, 1)
        prog_layout.addLayout(image_row)
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        prog_layout.addWidget(self.status_label)
        prog_layout.addWidget(self.progress_bar)

        # Summary banner — hidden until verification completes
        self.summary_label = QLabel()
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.summary_label.hide()
        prog_layout.addWidget(self.summary_label)

        layout.addWidget(prog_group)

        # Results table
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(
            ["Image", "Algorithm", "Result", "Stored Hash", "Calculated Hash"])
        hdr = self.results_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.Stretch)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        results_layout.addWidget(self.results_table)
        layout.addWidget(results_group)

    def set_container_path(self, path):
        """Called from main window when container is opened elsewhere."""
        self.path_edit.setText(path)
        self.start_btn.setEnabled(bool(path))

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open AFF4 Container", "", "AFF4 Files (*.aff4 *.zip);;All Files (*)"
        )
        if path:
            self.path_edit.setText(path)
            self.start_btn.setEnabled(True)

    def _start(self):
        path = self.path_edit.text().strip()
        if not path:
            return
        self._fail_count = 0
        self.results_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting...")
        self.summary_label.hide()
        self.summary_label.setStyleSheet(_SUMMARY_NEUTRAL_STYLE)
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        self._worker = VerifyWorker(path)
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.image_started.connect(self.current_image_label.setText)
        self._worker.image_started.connect(lambda name: self.status_label.setText("Hashing..."))
        self._worker.hash_result.connect(self._on_result)
        self._worker.status.connect(self.status_label.setText)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self.status_label.setText("Cancelling...")
        self.cancel_btn.setEnabled(False)

    def _on_result(self, image_name, algo, stored, calculated, valid):
        if not valid:
            self._fail_count += 1
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        result_text = "PASS" if valid else "FAIL"
        color = PASS_COLOR if valid else FAIL_COLOR
        for col, val in enumerate([image_name, algo, result_text, stored, calculated]):
            item = QTableWidgetItem(val)
            item.setBackground(color)
            self.results_table.setItem(row, col, item)

    def _on_error(self, msg):
        self.status_label.setText("Error: " + msg)

    def _on_finished(self):
        self.current_image_label.setText("-")
        self.status_label.setText("Hashing complete.")
        self.progress_bar.setValue(100)
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._worker = None

        if self._fail_count == 0:
            self.summary_label.setText("VERIFICATION PASSED")
            self.summary_label.setStyleSheet(_SUMMARY_PASS_STYLE)
        else:
            self.summary_label.setText(
                "VERIFICATION FAILED  —  %d hash mismatch%s" % (
                    self._fail_count, "es" if self._fail_count != 1 else ""))
            self.summary_label.setStyleSheet(_SUMMARY_FAIL_STYLE)
        self.summary_label.show()
