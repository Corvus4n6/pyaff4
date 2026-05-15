import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QListWidget, QListWidgetItem,
    QLineEdit, QGroupBox, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt

from pyaff4.gui.workers import AddImagesWorker


class AddImagesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Target container
        tgt_group = QGroupBox("Target Container (existing AFF4 file)")
        tgt_layout = QHBoxLayout(tgt_group)
        self.container_edit = QLineEdit()
        self.container_edit.setPlaceholderText("Path to existing .aff4 file...")
        self.container_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_container)
        tgt_layout.addWidget(self.container_edit)
        tgt_layout.addWidget(browse_btn)
        layout.addWidget(tgt_group)

        # Source files
        src_group = QGroupBox("Source Files / Folders")
        src_layout = QVBoxLayout(src_group)
        self.source_list = QListWidget()
        src_btn_row = QHBoxLayout()
        add_file_btn = QPushButton("Add File(s)...")
        add_file_btn.clicked.connect(self._add_files)
        add_folder_btn = QPushButton("Add Folder...")
        add_folder_btn.clicked.connect(self._add_folder)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        src_btn_row.addWidget(add_file_btn)
        src_btn_row.addWidget(add_folder_btn)
        src_btn_row.addWidget(remove_btn)
        src_btn_row.addStretch()
        src_layout.addWidget(self.source_list)
        src_layout.addLayout(src_btn_row)
        layout.addWidget(src_group)

        # Controls + progress
        ctrl_row = QHBoxLayout()
        self.start_btn = QPushButton("Add Images")
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        ctrl_row.addWidget(self.start_btn)
        ctrl_row.addWidget(self.cancel_btn)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addStretch()

    def _browse_container(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select AFF4 Container", "", "AFF4 Files (*.aff4 *.zip);;All Files (*)"
        )
        if path:
            self.container_edit.setText(path)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Files")
        for p in paths:
            if not self._already_in_list(p):
                self.source_list.addItem(p)

    def _add_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path and not self._already_in_list(path):
            self.source_list.addItem(path)

    def _already_in_list(self, path):
        for i in range(self.source_list.count()):
            if self.source_list.item(i).text() == path:
                return True
        return False

    def _remove_selected(self):
        for item in self.source_list.selectedItems():
            self.source_list.takeItem(self.source_list.row(item))

    def _start(self):
        container_path = self.container_edit.text().strip()
        sources = [self.source_list.item(i).text() for i in range(self.source_list.count())]
        if not container_path:
            QMessageBox.warning(self, "No Container", "Please select a target AFF4 container.")
            return
        if not sources:
            QMessageBox.warning(self, "No Sources", "Please add at least one source file or folder.")
            return

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting...")

        self._worker = AddImagesWorker(container_path, sources)
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.status.connect(self.status_label.setText)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self.cancel_btn.setEnabled(False)

    def _on_error(self, msg):
        self.status_label.setText("Error: " + msg)

    def _on_finished(self):
        self.status_label.setText("Done.")
        self.progress_bar.setValue(100)
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._worker = None
