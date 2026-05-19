import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from pyaff4 import container, rdfvalue, lexicon


class ContainerTab(QWidget):
    container_opened = Signal(str)  # emitted with file path when a container is opened

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # File picker row
        file_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("AFF4 container path...")
        self.path_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(self.path_edit)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        # Volume info
        vol_group = QGroupBox("Volume")
        vol_form = QFormLayout(vol_group)
        self.lbl_urn = QLabel("-")
        self.lbl_urn.setWordWrap(True)
        self.lbl_urn.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.lbl_version = QLabel("-")
        self.lbl_version.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.lbl_type = QLabel("-")
        self.lbl_type.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        vol_form.addRow("URN:", self.lbl_urn)
        vol_form.addRow("Version:", self.lbl_version)
        vol_form.addRow("Type:", self.lbl_type)
        layout.addWidget(vol_group)

        # Case info
        case_group = QGroupBox("Case Details")
        case_form = QFormLayout(case_group)
        self.lbl_case_name = QLabel("-")
        self.lbl_case_name.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.lbl_examiner = QLabel("-")
        self.lbl_examiner.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.lbl_description = QLabel("-")
        self.lbl_description.setWordWrap(True)
        self.lbl_description.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        case_form.addRow("Case Name:", self.lbl_case_name)
        case_form.addRow("Examiner:", self.lbl_examiner)
        case_form.addRow("Description:", self.lbl_description)
        layout.addWidget(case_group)

        # Image list
        img_group = QGroupBox("Images")
        img_layout = QVBoxLayout(img_group)
        self.image_table = QTableWidget(0, 3)
        self.image_table.setHorizontalHeaderLabels(["Name", "Size", "URN"])
        self.image_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.image_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.image_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.image_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.image_table.setSelectionBehavior(QTableWidget.SelectRows)
        img_layout.addWidget(self.image_table)
        layout.addWidget(img_group)

        layout.addStretch()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open AFF4 Container", "", "AFF4 Files (*.aff4 *.zip);;All Files (*)"
        )
        if path:
            self.load_container(path)

    def load_container(self, path):
        self.path_edit.setText(path)
        self._clear()
        try:
            urn = rdfvalue.URN.FromFileName(path)
            with container.Container.openURNtoContainer(urn) as volume:
                self.lbl_urn.setText(str(volume.urn))
                self.lbl_version.setText(str(volume.version))
                self.lbl_type.setText(type(volume).__name__)

                case = volume.getMetadata("CaseDetails")
                if case:
                    self.lbl_case_name.setText(str(case.caseName or "-"))
                    self.lbl_examiner.setText(str(case.examiner or "-"))
                    self.lbl_description.setText(str(case.caseDescription or "-"))

                self.image_table.setRowCount(0)
                for image in volume.images():
                    row = self.image_table.rowCount()
                    self.image_table.insertRow(row)
                    self.image_table.setItem(row, 0, QTableWidgetItem(str(image.name())))
                    try:
                        sz = volume.resolver.GetUnique(volume.urn, image.urn, volume.lexicon.streamSize)
                        if sz:
                            size_str = self._fmt_size(int(sz))
                        else:
                            with volume.resolver.AFF4FactoryOpen(image.urn, version=volume.version) as s:
                                size_str = self._fmt_size(s.Size())
                    except Exception:
                        size_str = "?"
                    self.image_table.setItem(row, 1, QTableWidgetItem(size_str))
                    self.image_table.setItem(row, 2, QTableWidgetItem(str(image.urn)))

            self.container_opened.emit(path)
        except Exception as e:
            self.lbl_urn.setText("Error: %s" % str(e))

    def _clear(self):
        for lbl in [self.lbl_urn, self.lbl_version, self.lbl_type,
                    self.lbl_case_name, self.lbl_examiner, self.lbl_description]:
            lbl.setText("-")
        self.image_table.setRowCount(0)

    @staticmethod
    def _fmt_size(n):
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024:
                return "%.1f %s" % (n, unit)
            n /= 1024
        return "%.1f PB" % n
