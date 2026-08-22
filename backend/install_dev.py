"""Registers the native-messaging host for LOCAL DEVELOPMENT only, before a
packaged .exe exists (see specs/02-native-host-spec.md, "Install
locations"). CI/the release build instead points the manifest directly at
the compiled ytdlx_backend.exe via manifest_installer.install() from
main.py itself — this script exists purely so `python main.py` can be
exercised end-to-end from a loaded-unpacked extension during development.

Usage:
    python backend/install_dev.py

Chrome/Firefox require the manifest's "path" to point at an executable, not
a Python script — so this writes a tiny .bat wrapper that invokes the
current interpreter against main.py, and points the manifest at that
wrapper instead of at python.exe or main.py directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.resolve()
WRAPPER_PATH = BACKEND_DIR / "ytdlx_backend_dev.bat"


def _write_dev_wrapper() -> Path:
    python_exe = sys.executable
    main_py = BACKEND_DIR / "ytdlx_backend" / "main.py"
    WRAPPER_PATH.write_text(
        f'@echo off\r\n"{python_exe}" "{main_py}" %*\r\n',
        encoding="utf-8",
    )
    return WRAPPER_PATH


def main() -> None:
    sys.path.insert(0, str(BACKEND_DIR))
    from ytdlx_backend.native_host import manifest_installer  # noqa: E402 (path insert above is required first)

    wrapper = _write_dev_wrapper()
    manifest_installer.install(wrapper)
    print(f"Native messaging host registered for local development, pointing at:\n  {wrapper}")
    print(
        "Remember: security/origin_validator.py and "
        "native_host/manifest_installer.py's CHROME_EXTENSION_IDS must "
        "include your local unpacked extension's id for Chrome to accept "
        "connections during development."
    )


if __name__ == "__main__":
    main()
