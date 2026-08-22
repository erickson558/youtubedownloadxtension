"""Native dialogs used during the download flow.

Per specs/02-native-host-spec.md, every download prompts for a destination
folder — there is no default/auto-save location and no "remember last
folder" shortcut, by deliberate design (specs/00-project-spec.md /
confirmed product decision), so this dialog is invoked unconditionally on
every request rather than cached.
"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, ttk

from ytdlx_backend.i18n.translator import Translator

DONATE_URL = "https://www.paypal.com/donate/?hosted_button_id=ZABFRXC2P3JQN"


def choose_download_folder(translator: Translator, parent: tk.Misc | None = None) -> Path | None:
    """Shows the native folder-picker. Returns None if the user cancelled."""
    chosen = filedialog.askdirectory(title=translator.t("choose_folder_title"), parent=parent)
    return Path(chosen) if chosen else None


def show_about_dialog(translator: Translator, parent: tk.Misc, version: str) -> None:
    window = tk.Toplevel(parent)
    window.title(translator.t("about_title"))
    window.resizable(False, False)

    ttk.Label(window, text=translator.t("about_title"), font=("", 12, "bold")).pack(padx=16, pady=(16, 4))
    ttk.Label(window, text=f"v{version}").pack(padx=16, pady=(0, 12))

    donate_button = ttk.Button(
        window,
        text=translator.t("about_donate"),
        command=lambda: webbrowser.open(DONATE_URL),
    )
    donate_button.pack(padx=16, pady=(0, 16))
