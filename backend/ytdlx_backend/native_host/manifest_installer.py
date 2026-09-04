"""Writes the native-messaging host manifest files and registers them with
each browser, per specs/02-native-host-spec.md.

Two manifest files are generated from one source of truth (HOST_NAME and
the extension's Firefox gecko id) because Chrome and Firefox are NOT
interchangeable here:

  - Chrome/Edge/Brave read `allowed_origins`, a list of
    "chrome-extension://<id>/" URLs.
  - Firefox reads `allowed_extensions`, a list of bare Gecko add-on id
    strings.

Using the wrong key name, or the wrong value shape, on the wrong browser is
a silent-failure bug (the host simply never launches, with no clear error
surfaced to the user) — see specs/03-security-spec.md item 3. This module
is the single place both files are produced, so they cannot drift
independently.

Runs on HKEY_CURRENT_USER so no admin elevation is required, and re-runs
(idempotently) on every app start so a moved/updated .exe path is always
reflected — see specs/02-native-host-spec.md, "Install locations".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HOST_NAME = "com.erickson558.ytdlx"
FIREFOX_EXTENSION_ID = "youtubedownloadxtension@erickson558.github.io"

# Derived from the "key" field pinned in extension/manifest.json (a fixed
# dev RSA public key, so "Load unpacked" gets the same id on every install
# instead of one derived unpredictably from the extension's folder path) —
# see specs/02-native-host-spec.md, "Native-messaging host manifests".
# Real-world bug this fixed: with this tuple empty, Chrome/Edge/Brave users
# got an immediate, silent connectNative failure on every click — the OS
# manifest's allowed_origins was written as `[]`, so Chrome rejected the
# native host before it ever launched. Add the Chrome Web Store id here
# too, once published — it does not replace this dev id, both can coexist.
CHROME_EXTENSION_IDS: tuple[str, ...] = ("fmogpkpcemljclegnfhgdmjlabbgjafc",)


def _manifest_dir() -> Path:
    base = Path.home() / "AppData" / "Local" / "ytdlx"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _write_manifest(path: Path, *, host_exe_path: Path, allowed_origins: list[str] | None, allowed_extensions: list[str] | None) -> None:
    manifest: dict = {
        "name": HOST_NAME,
        "description": "YouTube Download Extension native host",
        "path": str(host_exe_path),
        "type": "stdio",
    }
    if allowed_origins is not None:
        manifest["allowed_origins"] = allowed_origins
    if allowed_extensions is not None:
        manifest["allowed_extensions"] = allowed_extensions

    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _register_windows_registry(registry_path: str, manifest_path: Path) -> None:
    if sys.platform != "win32":
        return

    import winreg  # stdlib, Windows-only

    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path)
    try:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(manifest_path))
    finally:
        winreg.CloseKey(key)


def install(host_exe_path: Path) -> None:
    """Idempotently (re-)installs the native-messaging manifests for
    Chrome, Edge, and Firefox on Windows, pointed at `host_exe_path`.
    """
    manifest_dir = _manifest_dir()

    chrome_manifest_path = manifest_dir / f"{HOST_NAME}.chrome.json"
    firefox_manifest_path = manifest_dir / f"{HOST_NAME}.firefox.json"

    _write_manifest(
        chrome_manifest_path,
        host_exe_path=host_exe_path,
        allowed_origins=[f"chrome-extension://{ext_id}/" for ext_id in CHROME_EXTENSION_IDS],
        allowed_extensions=None,
    )
    _write_manifest(
        firefox_manifest_path,
        host_exe_path=host_exe_path,
        allowed_origins=None,
        allowed_extensions=[FIREFOX_EXTENSION_ID],
    )

    # Edge does not read Chrome's registry key — each browser is
    # registered separately even though the manifest content is identical.
    _register_windows_registry(
        rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}", chrome_manifest_path
    )
    _register_windows_registry(
        rf"Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}", chrome_manifest_path
    )
    _register_windows_registry(
        rf"Software\Mozilla\NativeMessagingHosts\{HOST_NAME}", firefox_manifest_path
    )
