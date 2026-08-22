"""Flat JSON key->string loader for the desktop app's UI strings.

specs/04-i18n-spec.md explains why this is a custom loader instead of
stdlib gettext: gettext needs .mo compilation and locale-directory
discovery that gets awkward inside a PyInstaller one-file frozen build,
whereas a flat JSON file bundled as PyInstaller `datas` is simpler and
equally correct for this app's small string set.

Fallback chain: requested locale -> "en" -> the literal key itself (a
missing key should be visibly wrong, never a blank string).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "es", "pt", "fr")


def _detect_windows_ui_locale() -> str | None:
    """Reads the Windows UI language directly via the Win32 API.

    Windows does NOT set LANG/LC_ALL/LC_MESSAGES by default — verified on a
    real Windows machine with a Spanish system locale, all three were unset
    — so the POSIX env-var check below silently never fires on this app's
    primary target platform, defeating multi-language auto-detection
    entirely. GetUserDefaultUILanguage() + locale.windows_locale (a stdlib
    mapping from Windows LCID to a POSIX-style locale string like "es_MX")
    is the reliable way to ask Windows what language the user's UI is in.
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        import locale as locale_module

        lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return locale_module.windows_locale.get(lcid)
    except (ImportError, AttributeError, OSError):
        return None


def detect_system_locale() -> str:
    windows_locale = _detect_windows_ui_locale()
    if windows_locale:
        primary = windows_locale.split("_")[0].lower()
        if primary in SUPPORTED_LOCALES:
            return primary

    # POSIX fallback (also covers a user/CI environment that explicitly
    # sets one of these to override the OS-reported language).
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            primary = value.split(".")[0].split("_")[0].lower()
            if primary in SUPPORTED_LOCALES:
                return primary

    return DEFAULT_LOCALE


class Translator:
    def __init__(self, locale: str | None = None) -> None:
        self.locale = locale if locale in SUPPORTED_LOCALES else detect_system_locale()
        self._messages = self._load(self.locale)
        self._default_messages = self._messages if self.locale == DEFAULT_LOCALE else self._load(DEFAULT_LOCALE)

    @staticmethod
    def _load(locale: str) -> dict[str, str]:
        path = LOCALES_DIR / f"{locale}.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def t(self, key: str) -> str:
        return self._messages.get(key) or self._default_messages.get(key) or key
