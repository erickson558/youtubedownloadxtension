"""Defense-in-depth check on top of the OS-level native-messaging manifest.

Chrome/Firefox already refuse to launch a native host for any
origin/extension not listed in the manifest's allowed_origins /
allowed_extensions (see specs/02-native-host-spec.md and
specs/03-security-spec.md item 2). This module re-checks the same identity
the browser passes on argv against a second, independently-maintained
allow-list compiled into this app, so a mistake in the *installed* manifest
file (e.g. one written by an older version of manifest_installer.py that
didn't get cleaned up) doesn't silently widen who can talk to this host.

Chrome/Edge/Brave invoke the host as:
    ytdlx_backend.exe chrome-extension://<id>/ [--parent-window=<hwnd>]
Firefox invokes it as:
    ytdlx_backend.exe <extension-id-string>
(Firefox passes the bare Gecko add-on id, not a URL — this asymmetry is the
same one documented in specs/02-native-host-spec.md for the manifest files
themselves.)
"""

from __future__ import annotations

# Kept in lockstep with extension/manifest.json — see
# .claude/agents/backend-engineer.md: a change to the extension's id or
# gecko.id must update this list in the same commit.
#
# "fmogpkpcemljclegnfhgdmjlabbgjafc" is derived from the "key" field pinned
# in extension/manifest.json (see manifest_installer.py's
# CHROME_EXTENSION_IDS, generated from the same key) — it keeps
# "Load unpacked" installs on Chrome/Edge/Brave at a fixed id instead of
# one derived unpredictably from the extension's folder path. Add the
# Chrome Web Store id here too, once published — it does not replace this
# dev id, both can coexist. Never leave this set empty and expect any
# Chrome caller to be accepted (fails closed, see is_allowed_caller below).
ALLOWED_CHROME_ORIGINS = frozenset(
    {
        "chrome-extension://fmogpkpcemljclegnfhgdmjlabbgjafc/",
    }
)

ALLOWED_FIREFOX_EXTENSION_IDS = frozenset(
    {
        "youtubedownloadxtension@erickson558.github.io",
    }
)


def is_allowed_caller(argv: list[str]) -> bool:
    """Returns True only if argv identifies a caller on one of the
    compiled-in allow-lists above. Called once at native-host startup;
    a False result must terminate the process without processing any
    messages.
    """
    if len(argv) < 2:
        # No identity was passed at all — never allow only-a-guess.
        return False

    caller = argv[1]

    # Fails closed: an empty allow-list means nothing is allowed, not
    # everything (specs/03-security-spec.md — never wildcard, never
    # implicitly permissive).
    if caller.startswith("chrome-extension://"):
        return caller in ALLOWED_CHROME_ORIGINS

    return caller in ALLOWED_FIREFOX_EXTENSION_IDS
