# -*- mode: python ; coding: utf-8 -*-
#
# Builds the windowed, console-free Windows executable that acts both as
# the native-messaging host and the tray/queue GUI (see
# ytdlx_backend/main.py and specs/02-native-host-spec.md).
#
# Run from the repo root or from backend/ — paths below are resolved
# relative to this spec file's own directory (SPECPATH, a PyInstaller
# builtin) so the result doesn't depend on the caller's working directory:
#
#   pyinstaller backend/pyinstaller.spec
#
# The `datas` entry for i18n/locales is required: without it, the
# translator.py loader (specs/04-i18n-spec.md) finds no locale JSON files
# inside the frozen onefile bundle and every string silently falls back to
# English, even for a Spanish/Portuguese/French system.

import os

block_cipher = None

a = Analysis(
    [os.path.join(SPECPATH, "ytdlx_backend", "main.py")],
    pathex=[SPECPATH],
    binaries=[],
    datas=[
        (
            os.path.join(SPECPATH, "ytdlx_backend", "i18n", "locales"),
            os.path.join("ytdlx_backend", "i18n", "locales"),
        ),
    ],
    hiddenimports=["yt_dlp"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ytdlx_backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # --windowed / --noconsole: no console window for this GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(SPECPATH, "ytdlx_backend", "assets", "icon.ico"),
)
