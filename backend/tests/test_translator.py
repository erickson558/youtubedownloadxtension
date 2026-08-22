import sys
from unittest.mock import patch

import pytest

from ytdlx_backend.i18n.translator import Translator, detect_system_locale


@pytest.mark.skipif(sys.platform != "win32", reason="exercises the Win32 UI-language API")
def test_detect_system_locale_uses_windows_ui_language_when_env_vars_unset(monkeypatch):
    # Regression test: Windows does not set LANG/LC_ALL/LC_MESSAGES by
    # default (confirmed on a real Windows machine with a Spanish system
    # locale — all three were unset), so detection must not depend on them
    # alone or it silently always falls back to English on the app's
    # primary target platform.
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)

    with patch("ytdlx_backend.i18n.translator._detect_windows_ui_locale", return_value="es_MX"):
        assert detect_system_locale() == "es"


def test_detect_system_locale_honors_posix_env_override(monkeypatch):
    monkeypatch.setenv("LC_ALL", "fr_FR.UTF-8")
    with patch("ytdlx_backend.i18n.translator._detect_windows_ui_locale", return_value=None):
        assert detect_system_locale() == "fr"


def test_detect_system_locale_falls_back_to_english_when_unresolvable(monkeypatch):
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    with patch("ytdlx_backend.i18n.translator._detect_windows_ui_locale", return_value=None):
        assert detect_system_locale() == "en"


def test_translator_falls_back_to_english_for_missing_key():
    translator = Translator(locale="es")
    assert translator.t("this_key_does_not_exist") == "this_key_does_not_exist"


def test_translator_loads_requested_locale():
    translator = Translator(locale="es")
    assert translator.t("app_title") == "Descargador de Video"
