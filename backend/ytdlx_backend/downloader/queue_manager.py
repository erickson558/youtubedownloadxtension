"""In-memory download queue shared by the native-messaging handler and the
GUI's queue/progress view (see specs/02-native-host-spec.md, message types
`queue.list` / `queue.snapshot`).

Each download runs on its own worker thread so a slow/stalled download
doesn't block the native-messaging read loop or the Tkinter event loop from
handling new requests.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ytdlx_backend.downloader.ytdlp_runner import DownloadError, download


@dataclass
class QueueItem:
    request_id: str
    url: str
    page_title: str
    status: str = "queued"  # queued -> downloading -> complete | error | cancelled
    percent: str = "0%"
    speed: str = ""
    eta: str = ""
    file_path: str | None = None
    error_message: str | None = None


class QueueManager:
    def __init__(self, on_update: Callable[[QueueItem], None] | None = None) -> None:
        self._items: dict[str, QueueItem] = {}
        self._lock = threading.Lock()
        self._on_update = on_update

    def snapshot(self) -> list[QueueItem]:
        with self._lock:
            return list(self._items.values())

    def start_download(self, request_id: str, url: str, page_title: str, destination_dir: Path) -> None:
        item = QueueItem(request_id=request_id, url=url, page_title=page_title, status="downloading")
        with self._lock:
            self._items[request_id] = item
        self._notify(item)

        thread = threading.Thread(
            target=self._run,
            args=(item, destination_dir),
            daemon=True,
        )
        thread.start()

    def _run(self, item: QueueItem, destination_dir: Path) -> None:
        def on_progress(percent: str, speed: str, eta: str) -> None:
            item.percent, item.speed, item.eta = percent, speed, eta
            self._notify(item)

        try:
            result_path = download(item.url, destination_dir, on_progress=on_progress)
            item.status = "complete"
            item.file_path = str(result_path)
        except DownloadError as exc:
            item.status = "error"
            item.error_message = str(exc)
        finally:
            self._notify(item)

    def _notify(self, item: QueueItem) -> None:
        if self._on_update:
            self._on_update(item)
