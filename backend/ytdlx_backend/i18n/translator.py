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
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "es", "pt", "fr")


def detect_system_locale() -> str:
    # locale.getdefaultlocale() is deprecated (and removed in newer
    # Pythons); reading the standard POSIX env vars directly is simpler and
    # forward-compatible, and Windows Python also sets LANG in most
    # launch contexts relevant to this app (PyInstaller-frozen GUI).
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
