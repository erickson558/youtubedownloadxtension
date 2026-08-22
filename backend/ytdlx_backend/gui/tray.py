"""System tray icon, shown for the lifetime of the app.

Runs pystray's own loop on a background thread while Tkinter's mainloop
owns the main thread — Tkinter must run on the main thread on macOS, a
constraint kept here even though only a Windows build is packaged/released
initially, since the source is meant to stay portable.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

import pystray
from PIL import Image

from ytdlx_backend.i18n.translator import Translator

ICON_PATH = Path(__file__).parent.parent / "assets" / "icon.ico"


class TrayIcon:
    def __init__(self, translator: Translator, on_open: Callable[[], None], on_quit: Callable[[], None]) -> None:
        self._on_open = on_open
        self._on_quit = on_quit

        image = (
            Image.open(ICON_PATH)
            if ICON_PATH.exists()
            else Image.new("RGBA", (64, 64), (211, 51, 51, 255))
        )
        self._icon = pystray.Icon(
            "ytdlx",
            icon=image,
            title=translator.t("app_title"),
            menu=pystray.Menu(
                pystray.MenuItem(translator.t("tray_open"), self._handle_open, default=True),
                pystray.MenuItem(translator.t("tray_quit"), self._handle_quit),
            ),
        )

    def _handle_open(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._on_open()

    def _handle_quit(self, icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        icon.stop()
        self._on_quit()

    def start(self) -> None:
        threading.Thread(target=self._icon.run, daemon=True).start()

    def stop(self) -> None:
        self._icon.stop()
