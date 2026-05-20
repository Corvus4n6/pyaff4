import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QListWidget, QLineEdit,
    QGroupBox, QFormLayout, QTextEdit, QMessageBox, QSizePolicy,
    QComboBox
)
from PySide6.QtCore import Qt

from pyaff4.gui.workers import CreateVolumeWorker


class CreateVolumeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Output path
        out_group = QGroupBox("Output File")
        out_layout = QHBoxLayout(out_group)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Save new .aff4 container as...")
        self.output_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output)
        out_layout.addWidget(self.output_edit)
        out_layout.addWidget(browse_btn)
        layout.addWidget(out_group)

        # Case metadata
        meta_group = QGroupBox("Case Metadata (optional)")
        meta_form = QFormLayout(meta_group)
        self.case_name_edit = QLineEdit()
        self.examiner_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        meta_form.addRow("Case Name:", self.case_name_edit)
        meta_form.addRow("Examiner:", self.examiner_edit)
        meta_form.addRow("Description:", self.description_edit)
        layout.addWidget(meta_group)

        # Source files
        src_group = QGroupBox("Initial Files / Folders (optional)")
        src_layout = QVBoxLayout(src_group)
        self.source_list = QListWidget()
        src_btn_row = QHBoxLayout()
        add_file_btn = QPushButton("Add File(s)...")
        add_file_btn.clicked.connect(self._add_files)
        add_folder_btn = QPushButton("Add Folder...")
        add_folder_btn.clicked.connect(self._add_folder)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        self.path_mode_combo = QComboBox()
        self.path_mode_combo.addItems([
            "Store full paths",
            "Store relative paths",
            "Strip paths",
        ])
        self.path_mode_combo.setToolTip(
            "Full paths: store the complete original filesystem path\n"
            "Relative paths: store path relative to the parent of each selected item\n"
            "Strip paths: store filename only, no directory information"
        )
        src_btn_row.addWidget(add_file_btn)
        src_btn_row.addWidget(add_folder_btn)
        src_btn_row.addWidget(remove_btn)
        src_btn_row.addSpacing(12)
        src_btn_row.addWidget(QLabel("Path storage:"))
        src_btn_row.addWidget(self.path_mode_combo)
        src_btn_row.addStretch()
        src_layout.addWidget(self.source_list)
        src_layout.addLayout(src_btn_row)
        layout.addWidget(src_group)

        # Controls
        ctrl_row = QHBoxLayout()
        self.create_btn = QPushButton("Create Volume")
        self.create_btn.clicked.connect(self._start)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        ctrl_row.addWidget(self.create_btn)
        ctrl_row.addWidget(self.cancel_btn)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addStretch()

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save AFF4 Container", "", "AFF4 Files (*.aff4);;All Files (*)"
        )
        if path:
            if not path.endswith(".aff4"):
                path += ".aff4"
            self.output_edit.setText(path)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Files")
        for p in paths:
            if not self._in_list(p):
                self.source_list.addItem(p)

    def _add_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path and not self._in_list(path):
            self.source_list.addItem(path)

    def _in_list(self, path):
        for i in range(self.source_list.count()):
            if self.source_list.item(i).text() == path:
                return True
        return False

    def _remove_selected(self):
        for item in self.source_list.selectedItems():
            self.source_list.takeItem(self.source_list.row(item))

    def _start(self):
        output = self.output_edit.text().strip()
        if not output:
            QMessageBox.warning(self, "No Output Path", "Please select an output path for the new container.")
            return

        case_name = self.case_name_edit.text().strip()
        examiner = self.examiner_edit.text().strip()
        description = self.description_edit.toPlainText().strip()
        sources = [self.source_list.item(i).text() for i in range(self.source_list.count())]
        path_mode = self.path_mode_combo.currentText()

        # Pre-flight: abort if any stored paths would collide
        if sources:
            collisions = CreateVolumeWorker.find_path_collisions(sources, path_mode)
            if collisions:
                lines = []
                for stored_path, originals in sorted(collisions.items()):
                    lines.append('"%s"  would be written by:' % stored_path)
                    for orig in originals:
                        lines.append('    • %s' % orig)
                    lines.append('')
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Path Collision Detected")
                box.setText(
                    "%d stored path%s would be shared by more than one source file.\n\n"
                    "No files have been written.\n\n"
                    "To fix: switch to a different path storage mode, or remove the "
                    "conflicting sources from the list."
                    % (len(collisions), "s" if len(collisions) != 1 else "")
                )
                box.setDetailedText("\n".join(lines).rstrip())
                box.exec()
                return

        self.create_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Creating container...")

        self._worker = CreateVolumeWorker(output, case_name, examiner, description, sources,
                                          self.path_mode_combo.currentText())
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
        self.progress_bar.setValue(100)
        self.create_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._worker = None
