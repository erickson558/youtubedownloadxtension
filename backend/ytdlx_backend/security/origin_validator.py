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
# Deliberately fails closed while empty (see is_allowed_caller below): add
# the real Chrome Web Store id once published, or a local dev id (derived
# from extension/manifest.json's "key" field) for local testing — never
# leave this empty and expect Chrome callers to be accepted.
ALLOWED_CHROME_ORIGINS = frozenset(
    {
        # "chrome-extension://<id>/",
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
