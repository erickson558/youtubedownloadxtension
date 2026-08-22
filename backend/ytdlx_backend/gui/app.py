"""Main Tkinter window: shows the download queue/progress. Runs alongside
a system tray icon (see tray.py) — closing this window hides it rather than
exiting the process; only the tray's "Quit" fully exits (see
specs/02-native-host-spec.md, "Process model").
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ytdlx_backend.__version__ import __version__
from ytdlx_backend.downloader.queue_manager import QueueItem
from ytdlx_backend.gui.dialogs import show_about_dialog
from ytdlx_backend.i18n.translator import Translator

ICON_PATH = Path(__file__).parent.parent / "assets" / "icon.ico"


class MainWindow:
    def __init__(self, translator: Translator | None = None) -> None:
        self.translator = translator or Translator()
        self.root = tk.Tk()
        self.root.title(self.translator.t("app_title"))
        self.root.geometry("480x320")
        if ICON_PATH.exists():
            try:
                self.root.iconbitmap(str(ICON_PATH))
            except tk.TclError:
                pass  # iconbitmap can fail on non-Windows Tk builds; non-fatal

        self._build_menu()
        self._build_queue_view()

        # Hiding instead of destroying keeps the tray icon's "Open" action
        # meaningful after the user closes the window.
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label=self.translator.t("menu_about"),
            command=lambda: show_about_dialog(self.translator, self.root, __version__),
        )
        menubar.add_cascade(label=self.translator.t("menu_about"), menu=help_menu)
        self.root.config(menu=menubar)

    def _build_queue_view(self) -> None:
        columns = ("title", "status", "progress")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings")
        self.tree.heading("title", text=self.translator.t("queue_column_title"))
        self.tree.heading("status", text=self.translator.t("queue_column_status"))
        self.tree.heading("progress", text=self.translator.t("queue_column_progress"))
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def upsert_queue_item(self, item: QueueItem) -> None:
        # Scheduled via `after` so this is safe to call from the
        # background download thread (queue_manager.py's on_update
        # callback) instead of touching Tk widgets off the main thread.
        self.root.after(0, self._upsert_queue_item_on_main_thread, item)

    def _upsert_queue_item_on_main_thread(self, item: QueueItem) -> None:
        status_label = self.translator.t(f"status_{item.status}")
        values = (item.page_title or item.url, status_label, item.percent)
        if self.tree.exists(item.request_id):
            self.tree.item(item.request_id, values=values)
        else:
            self.tree.insert("", tk.END, iid=item.request_id, values=values)

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()

    def hide(self) -> None:
        self.root.withdraw()

    def run(self) -> None:
        self.root.mainloop()
