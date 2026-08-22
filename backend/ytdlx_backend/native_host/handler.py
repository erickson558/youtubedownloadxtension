"""Dispatches incoming native-messaging requests to the download queue and
sends back progress/completion/error messages.

See specs/02-native-host-spec.md ("Message types", "Download flow") for the
contract this implements. Error messages sent back over the wire are kept
short and free of stack traces or local filesystem details, per
specs/03-security-spec.md item 6 — full details go to the log file only.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from ytdlx_backend.downloader.queue_manager import QueueItem, QueueManager
from ytdlx_backend.native_host.protocol import send_message
from ytdlx_backend.security.path_sanitizer import UnsafePathError, validate_save_path

logger = logging.getLogger(__name__)


class RequestHandler:
    def __init__(
        self,
        choose_folder: Callable,
        on_queue_update: Callable[[QueueItem], None] | None = None,
    ) -> None:
        """`choose_folder` is a zero-arg callable that shows the native
        folder-picker dialog and returns a Path, or None if the user
        cancelled. Injected rather than imported directly so this class
        doesn't depend on Tkinter and can be unit-tested headlessly.

        `on_queue_update`, if given, is called on every queue item change
        in addition to the native-messaging reply — this is how main.py
        keeps the GUI's queue view in sync without the handler needing to
        know the GUI exists.
        """
        self._choose_folder = choose_folder
        self._on_queue_update = on_queue_update
        self._queue = QueueManager(on_update=self._handle_queue_update)

    def _handle_queue_update(self, item: QueueItem) -> None:
        if self._on_queue_update:
            self._on_queue_update(item)
        self._send_progress(item)

    def handle(self, message: dict) -> None:
        message_type = message.get("type")

        if message_type == "download.request":
            self._handle_download_request(message)
        elif message_type == "queue.list":
            send_message(
                {
                    "type": "queue.snapshot",
                    "items": [self._item_to_dict(item) for item in self._queue.snapshot()],
                }
            )
        else:
            logger.warning("unrecognized message type: %r", message_type)

    def _handle_download_request(self, message: dict) -> None:
        request_id = message.get("requestId", "")
        url = message.get("url", "")
        page_title = message.get("pageTitle", "")

        if not url or not request_id:
            send_message({"type": "download.error", "requestId": request_id, "message": "invalid request"})
            return

        chosen_root = self._choose_folder()
        if chosen_root is None:
            send_message({"type": "download.error", "requestId": request_id, "message": "cancelled"})
            return

        try:
            # The user's own folder-picker choice is itself the trusted
            # root; validate_save_path here mainly guards against the
            # picker returning something unexpected (e.g. a UNC path).
            destination_dir = validate_save_path(chosen_root, chosen_root)
        except UnsafePathError:
            logger.exception("rejected save location")
            send_message({"type": "download.error", "requestId": request_id, "message": "invalid save location"})
            return

        self._queue.start_download(request_id, url, page_title, destination_dir)

    def _send_progress(self, item: QueueItem) -> None:
        if item.status == "downloading":
            send_message(
                {
                    "type": "download.progress",
                    "requestId": item.request_id,
                    "percent": item.percent,
                    "speed": item.speed,
                    "eta": item.eta,
                }
            )
        elif item.status == "complete":
            send_message({"type": "download.complete", "requestId": item.request_id, "filePath": item.file_path})
        elif item.status == "error":
            logger.error("download %s failed: %s", item.request_id, item.error_message)
            send_message(
                {
                    "type": "download.error",
                    "requestId": item.request_id,
                    "message": "download failed",
                }
            )

    @staticmethod
    def _item_to_dict(item: QueueItem) -> dict:
        return {
            "requestId": item.request_id,
            "url": item.url,
            "pageTitle": item.page_title,
            "status": item.status,
            "percent": item.percent,
        }
