"""Runs yt-dlp as a subprocess and streams progress back.

specs/02-native-host-spec.md ("yt-dlp invocation contract") and
specs/03-security-spec.md item 1 govern this file: yt-dlp is invoked with
shell=False and an explicit argument list, never a shell string built by
concatenating the URL — the URL originates from an untrusted web page
reached through the extension. A literal "--" always precedes the URL
argument so a URL crafted to start with "-" can never be parsed as a
yt-dlp flag instead of a positional argument.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

# yt-dlp emits one line per progress update when given --newline; this
# template produces a fixed, pipe-delimited format so progress is parsed
# from a known shape instead of regexing yt-dlp's human-oriented default
# progress bar.
PROGRESS_TEMPLATE = "download:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s"

STALL_TIMEOUT_SECONDS = 120  # kill a download with no progress update for this long
_WATCHDOG_POLL_SECONDS = 5

# In a normal `python main.py` dev run, sys.executable is a real python.exe,
# so `[sys.executable, "-m", "yt_dlp", ...]` works as expected. Inside a
# PyInstaller --onefile build, sys.executable is ytdlx_backend.exe itself —
# it has no built-in "-m" support, so that same invocation would just try
# to re-run this app with unrecognized arguments. Instead, the frozen exe
# is re-invoked with this sentinel as argv[1]; main.py checks for it before
# doing anything else and, if present, imports yt_dlp and runs its own CLI
# entry point in this process instead of starting the app normally. This
# keeps yt-dlp running as a genuine child *process* (crash isolation from
# the GUI, --newline streaming) in both dev and frozen builds, rather than
# needing two different execution strategies at the call site.
INTERNAL_YTDLP_WORKER_ARG = "--ytdlx-internal-run-yt-dlp"


def maybe_run_as_yt_dlp_worker() -> None:
    """Call once, first thing, from the app's entry point. If this process
    was launched as the internal yt-dlp worker (see INTERNAL_YTDLP_WORKER_ARG
    above), runs yt-dlp's CLI and exits; otherwise returns immediately and
    the caller proceeds with normal app startup.
    """
    if len(sys.argv) < 2 or sys.argv[1] != INTERNAL_YTDLP_WORKER_ARG:
        return

    import yt_dlp  # imported lazily so normal app startup never pays for it

    sys.argv = [sys.argv[0], *sys.argv[2:]]
    yt_dlp.main()  # calls sys.exit() itself with yt-dlp's own return code


def _yt_dlp_command_prefix() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, INTERNAL_YTDLP_WORKER_ARG]
    return [sys.executable, "-m", "yt_dlp"]


class DownloadError(RuntimeError):
    """Raised when yt-dlp fails, stalls, or reports no output file."""


def download(
    url: str,
    destination_dir: Path,
    *,
    on_progress: Callable[[str, str, str], None] | None = None,
) -> Path:
    """Downloads `url` into `destination_dir` via yt-dlp.

    `destination_dir` must already have been validated by
    security.path_sanitizer.validate_save_path — this function trusts its
    caller on that point rather than re-validating, since it isn't given
    the original user-chosen root needed to do that check itself.

    Returns the path to the downloaded file. Raises DownloadError on
    failure or stall.
    """
    output_template = str(destination_dir / "%(title)s.%(ext)s")

    args = [
        *_yt_dlp_command_prefix(),
        "--newline",
        "--progress-template",
        PROGRESS_TEMPLATE,
        "-o",
        output_template,
        "--print",
        "after_move:filepath",
        "--",
        url,
    ]

    process = subprocess.Popen(
        args,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    last_progress_at = time.monotonic()
    stalled = threading.Event()
    stop_watchdog = threading.Event()

    def watchdog() -> None:
        # Runs on a separate thread because the main thread is blocked
        # reading process output line-by-line, which would otherwise never
        # notice a hang (a subprocess that stops producing output blocks
        # the iterator forever, not just until a timeout).
        while not stop_watchdog.wait(_WATCHDOG_POLL_SECONDS):
            if time.monotonic() - last_progress_at > STALL_TIMEOUT_SECONDS:
                stalled.set()
                process.kill()
                return

    watchdog_thread = threading.Thread(target=watchdog, daemon=True)
    watchdog_thread.start()

    final_path: str | None = None

    try:
        for raw_line in process.stdout:  # type: ignore[union-attr]
            line = raw_line.rstrip("\n")
            last_progress_at = time.monotonic()

            if line.startswith("download:"):
                _, _, rest = line.partition(":")
                percent, _, remainder = rest.partition("|")
                speed, _, eta = remainder.partition("|")
                if on_progress:
                    on_progress(percent, speed, eta)
            elif line:
                # Any other non-empty line is a candidate for the final
                # file path (emitted via --print after_move:filepath) or
                # diagnostic output; the last one wins.
                final_path = line

        return_code = process.wait()
    finally:
        stop_watchdog.set()
        if process.poll() is None:
            process.kill()

    if stalled.is_set():
        raise DownloadError(f"no progress for {STALL_TIMEOUT_SECONDS}s, download aborted")

    if return_code != 0:
        raise DownloadError(f"yt-dlp exited with code {return_code}")

    if not final_path:
        raise DownloadError("yt-dlp did not report a final file path")

    return Path(final_path)
