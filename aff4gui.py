#!/usr/bin/env python3
import sys


def main():
    # Handle --version before touching Qt so it works headlessly in CI.
    if "--version" in sys.argv:
        from pyaff4 import _version as _pkg_version
        v = _pkg_version.get_versions()
        print(v.get("semver", v.get("version", "unknown")))
        return

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("Error: PySide6 is required for the GUI. Install it with: pip install PySide6", file=sys.stderr)
        sys.exit(1)

    from pyaff4.gui.main_window import MainWindow
    app = QApplication(sys.argv)
    app.setApplicationName("AFF4 Forensic Tool")
    app.setOrganizationName("pyaff4")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
