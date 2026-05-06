import pytest
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def pytest_addoption(parser):
    parser.addoption(
        "--binary",
        action="store",
        default=None,
        help=(
            "Path to a compiled aff4 binary to test. "
            "Relative paths are resolved from the repo root. "
            "Defaults to `python aff4.py`."
        ),
    )


@pytest.fixture(scope="session")
def aff4_cmd(request):
    """Return the base command list used to invoke aff4 in all tests."""
    binary = request.config.getoption("--binary")
    if binary:
        path = Path(binary)
        if not path.is_absolute():
            path = REPO_ROOT / path
        return [str(path)]
    return [sys.executable, str(REPO_ROOT / "aff4.py")]


@pytest.fixture
def run_aff4(aff4_cmd):
    """
    Return a helper that runs the aff4 command with the given arguments
    and returns the CompletedProcess result. Does not raise on non-zero exit.
    """
    def _run(*args):
        return subprocess.run(
            aff4_cmd + [str(a) for a in args],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
    return _run
