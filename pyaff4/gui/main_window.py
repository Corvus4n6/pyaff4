from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QLabel
)
from PySide6.QtCore import Qt

from pyaff4 import _version as _pkg_version
from pyaff4.gui.tab_container import ContainerTab
from pyaff4.gui.tab_verify import VerifyTab
from pyaff4.gui.tab_add import AddImagesTab
from pyaff4.gui.tab_create import CreateVolumeTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        v = _pkg_version.get_versions()
        version_str = v.get("semver", v.get("version", "unknown"))
        self.setWindowTitle("AFF4 Imager v%s" % version_str)
        self.resize(900, 700)
        self._setup_ui()

    def _setup_ui(self):
        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        self.container_tab = ContainerTab()
        self.verify_tab = VerifyTab()
        self.add_tab = AddImagesTab()
        self.create_tab = CreateVolumeTab()

        tabs.addTab(self.create_tab, "Create Volume")
        tabs.addTab(self.verify_tab, "Verify Volume")
        tabs.addTab(self.add_tab, "Add to Volume")
        tabs.addTab(self.container_tab, "View Volume")

        # When a container is opened in the Container tab, pre-fill Verify
        self.container_tab.container_opened.connect(self.verify_tab.set_container_path)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
