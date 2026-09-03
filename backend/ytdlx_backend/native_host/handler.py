"""Dispatches incoming native-messaging requests to the download queue and
sends back progress/completion/error messages.

See specs/02-native-host-spec.md ("Message types", "Download flow") for the
contract this implements. Error messages sent back over the wire are kept
short and free of stack traces or local filesystem details, per
specs/03-security-spec.md item 6 — full details go to the log file only.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from ytdlx_backend.downloader.queue_manager import QueueItem, QueueManager
from ytdlx_backend.native_host.protocol import send_message
from ytdlx_backend.security.path_sanitizer import UnsafePathError, validate_save_path

logger = logging.getLogger(__name__)

Sink = Callable[[dict], None]


class RequestHandler:
    def __init__(
        self,
        choose_folder: Callable,
        on_queue_update: Callable[[QueueItem], None] | None = None,
        on_settled: Callable[[], None] | None = None,
    ) -> None:
        """`choose_folder` is a zero-arg callable that shows the native
        folder-picker dialog and returns a Path, or None if the user
        cancelled. Injected rather than imported directly so this class
        doesn't depend on Tkinter and can be unit-tested headlessly.

        `on_queue_update`, if given, is called on every queue item change
        in addition to the native-messaging reply — this is how main.py
        keeps the GUI's queue view in sync without the handler needing to
        know the GUI exists.

        `on_settled`, if given, is called every time a `download.request`
        reaches a terminal outcome (complete, error, cancelled, or
        rejected outright) *and* no other request is still queued or
        downloading — this is how main.py auto-closes a browser-launched
        instance once it has nothing left to do (see specs/02-native-host-spec.md,
        "Auto-close on settle"). Never called while any download is still
        in flight, so a batch of requests only triggers it once, after the
        last one finishes.
        """
        self._choose_folder = choose_folder
        self._on_queue_update = on_queue_update
        self._on_settled = on_settled
        self._queue = QueueManager(on_update=self._handle_queue_update)
        # Maps requestId -> where to send *this specific request's*
        # responses. A single ytdlx_backend.exe process can be juggling one
        # stdio connection (its own direct browser Port) plus any number of
        # forwarded connections from other browser-launched processes that
        # lost the single-instance race (see main.py) -- without this,
        # every response went to this process's own stdout unconditionally,
        # which silently orphaned every download started through a
        # forwarded connection: the response was sent, just never to the
        # browser that was actually waiting on it. Guarded by a lock since
        # a download's progress callback fires from its own worker thread.
        self._sinks: dict[str, Sink] = {}
        self._sinks_lock = threading.Lock()

    def _handle_queue_update(self, item: QueueItem) -> None:
        if self._on_queue_update:
            self._on_queue_update(item)
        self._send_progress(item)

    def handle(self, message: dict, respond: Sink | None = None) -> None:
        """`respond`, if given, is where this message's response(s) go
        instead of this process's own stdout — see the `_sinks` comment
        above. Defaults to `send_message` (stdout) for the primary
        instance's own direct browser connection.
        """
        sink = respond or send_message
        message_type = message.get("type")

        if message_type == "download.request":
            self._handle_download_request(message, sink)
        elif message_type == "queue.list":
            sink(
                {
                    "type": "queue.snapshot",
                    "items": [self._item_to_dict(item) for item in self._queue.snapshot()],
                }
            )
        else:
            logger.warning("unrecognized message type: %r", message_type)

    def _handle_download_request(self, message: dict, sink: Sink) -> None:
        request_id = message.get("requestId", "")
        url = message.get("url", "")
        page_title = message.get("pageTitle", "")

        if not url or not request_id:
            sink({"type": "download.error", "requestId": request_id, "message": "invalid request"})
            self._maybe_settle()
            return

        with self._sinks_lock:
            self._sinks[request_id] = sink

        chosen_root = self._choose_folder()
        if chosen_root is None:
            sink({"type": "download.error", "requestId": request_id, "message": "cancelled"})
            self._release_sink(request_id)
            self._maybe_settle()
            return

        try:
            # The user's own folder-picker choice is itself the trusted
            # root; validate_save_path here mainly guards against the
            # picker returning something unexpected (e.g. a UNC path).
            destination_dir = validate_save_path(chosen_root, chosen_root)
        except UnsafePathError:
            logger.exception("rejected save location")
            sink({"type": "download.error", "requestId": request_id, "message": "invalid save location"})
            self._release_sink(request_id)
            self._maybe_settle()
            return

        self._queue.start_download(request_id, url, page_title, destination_dir)

    def _release_sink(self, request_id: str) -> None:
        with self._sinks_lock:
            self._sinks.pop(request_id, None)

    def _sink_for(self, request_id: str) -> Sink:
        with self._sinks_lock:
            return self._sinks.get(request_id, send_message)

    def has_active_downloads(self) -> bool:
        """True if any request is still queued or in progress. Checked
        before firing `on_settled` so a batch of requests only triggers
        an auto-close once, after the *last* one finishes, not after each
        one.
        """
        return any(item.status in ("queued", "downloading") for item in self._queue.snapshot())

    def _maybe_settle(self) -> None:
        if self._on_settled and not self.has_active_downloads():
            self._on_settled()

    def _send_progress(self, item: QueueItem) -> None:
        sink = self._sink_for(item.request_id)
        if item.status == "downloading":
            sink(
                {
                    "type": "download.progress",
                    "requestId": item.request_id,
                    "percent": item.percent,
                    "speed": item.speed,
                    "eta": item.eta,
                }
            )
        elif item.status == "complete":
            sink({"type": "download.complete", "requestId": item.request_id, "filePath": item.file_path})
            self._release_sink(item.request_id)
            self._maybe_settle()
        elif item.status == "error":
            logger.error("download %s failed: %s", item.request_id, item.error_message)
            sink(
                {
                    "type": "download.error",
                    "requestId": item.request_id,
                    "message": "download failed",
                }
            )
            self._release_sink(item.request_id)
            self._maybe_settle()

    @staticmethod
    def _item_to_dict(item: QueueItem) -> dict:
        return {
            "requestId": item.request_id,
            "url": item.url,
            "pageTitle": item.page_title,
            "status": item.status,
            "percent": item.percent,
        }
