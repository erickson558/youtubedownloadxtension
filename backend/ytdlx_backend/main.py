"""Entry point. Same executable serves two roles (specs/02-native-host-spec.md,
"Process model"):

1. The browser launches it as the WebExtensions native-messaging host,
   talking to it purely over stdin/stdout with no GUI involved.
2. A user double-clicking the .exe gets a windowed app with a system tray
   icon showing the download queue.

Only one instance should ever own the GUI/tray at a time. A fixed local
loopback port is used as a simple mutex: whichever process binds it first
becomes "the" instance and owns the window; any later process (typically a
second browser-launched native-messaging process) forwards its request to
that instance over the same port and exits, instead of starting a second
competing tray icon (specs/02-native-host-spec.md).
"""

from __future__ import annotations

import json
import logging
import socket
import sys
import threading
from pathlib import Path

from ytdlx_backend.gui.app import MainWindow
from ytdlx_backend.gui.dialogs import choose_download_folder
from ytdlx_backend.gui.tray import TrayIcon
from ytdlx_backend.i18n.translator import Translator
from ytdlx_backend.native_host import manifest_installer
from ytdlx_backend.native_host.handler import RequestHandler
from ytdlx_backend.native_host.protocol import read_message
from ytdlx_backend.security.origin_validator import is_allowed_caller

logger = logging.getLogger(__name__)

# Arbitrary fixed loopback port, used only as a same-machine mutex/handoff
# channel — never exposed beyond 127.0.0.1.
SINGLE_INSTANCE_PORT = 51737


def _is_native_messaging_launch() -> bool:
    # The browser connects the host's stdin to a pipe, never a terminal;
    # a user double-clicking the .exe gets an interactive (or absent, for
    # a windowed/no-console build) stdin instead.
    try:
        return not sys.stdin.isatty()
    except (AttributeError, ValueError):
        return True  # no console at all (a --windowed PyInstaller build): treat as native mode


def _executable_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(__file__).resolve()


def _try_claim_single_instance() -> socket.socket | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        sock.listen(5)
        return sock
    except OSError:
        sock.close()
        return None


def _forward_request(message: dict) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", SINGLE_INSTANCE_PORT), timeout=2) as conn:
            conn.sendall(json.dumps(message).encode("utf-8") + b"\n")
        return True
    except OSError:
        logger.warning("could not forward request to running instance")
        return False


def _stdio_read_loop(handler: RequestHandler) -> None:
    while True:
        message = read_message()
        if message is None:
            return
        handler.handle(message)


def _accept_forwarded_requests(server_socket: socket.socket, handler: RequestHandler) -> None:
    while True:
        conn, _addr = server_socket.accept()
        with conn:
            data = b""
            while not data.endswith(b"\n"):
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
        if data:
            handler.handle(json.loads(data.decode("utf-8")))


def _run_as_forwarder() -> None:
    """A native-messaging process that lost the single-instance race: relay
    every message it receives from the browser to the running instance."""
    while True:
        message = read_message()
        if message is None:
            return
        _forward_request(message)


def _choose_folder_from_worker_thread(translator: Translator, window: MainWindow) -> Path | None:
    """`RequestHandler.handle()` runs on the stdio-read / forwarded-request
    worker threads (see _stdio_read_loop, _accept_forwarded_requests), but
    Tkinter widgets may only be touched from the main thread. This bridges
    the synchronous folder-picker call onto the main thread via `after()`
    and blocks the calling worker thread until it has an answer.
    """
    result: dict[str, Path | None] = {}
    done = threading.Event()

    def run_on_main_thread() -> None:
        result["value"] = choose_download_folder(translator, window.root)
        done.set()

    window.root.after(0, run_on_main_thread)
    done.wait()
    return result.get("value")


def _run_as_primary_instance(server_socket: socket.socket, *, start_hidden: bool) -> None:
    manifest_installer.install(_executable_path())

    translator = Translator()
    window = MainWindow(translator)
    handler = RequestHandler(
        choose_folder=lambda: _choose_folder_from_worker_thread(translator, window),
        on_queue_update=window.upsert_queue_item,
    )

    def quit_app() -> None:
        tray.stop()
        window.root.quit()

    tray = TrayIcon(translator, on_open=window.show, on_quit=quit_app)
    tray.start()

    threading.Thread(target=_stdio_read_loop, args=(handler,), daemon=True).start()
    threading.Thread(target=_accept_forwarded_requests, args=(server_socket, handler), daemon=True).start()

    if start_hidden:
        window.hide()  # a browser-triggered launch shouldn't steal focus with a visible window
    window.run()


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    native_launch = _is_native_messaging_launch()

    if native_launch and not is_allowed_caller(sys.argv):
        # Fails closed (specs/03-security-spec.md): no response at all for
        # an unrecognized caller, not an error that would confirm a host is
        # listening.
        sys.exit(1)

    server_socket = _try_claim_single_instance()
    if server_socket is None:
        if native_launch:
            _run_as_forwarder()
            return
        # A second GUI launch while one is already running: nothing useful
        # to do but exit — the existing tray icon already represents the app.
        return

    _run_as_primary_instance(server_socket, start_hidden=native_launch)


if __name__ == "__main__":
    main()
