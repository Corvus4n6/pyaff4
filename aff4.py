# Entry point shim — implementation lives in pyaff4/cli.py.
# Keeping this file allows `python aff4.py` and PyInstaller to work
# without any changes to their invocation.
from pyaff4.cli import main

if __name__ == "__main__":
    main()
