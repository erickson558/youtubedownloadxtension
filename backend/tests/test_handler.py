"""Covers the requestId -> sink routing in RequestHandler.

This is what a forwarded native-messaging connection (see main.py,
_handle_forwarded_connection) depends on to get its download's responses
back at all: before this routing existed, every response was sent
unconditionally to this process's own stdout, which silently dropped every
response for a request that arrived over a forwarded connection instead of
this process's own direct browser connection.
"""

from __future__ import annotations

from ytdlx_backend.downloader.queue_manager import QueueItem
from ytdlx_backend.native_host.handler import RequestHandler


def _handler(choose_folder=None) -> RequestHandler:
    return RequestHandler(choose_folder=choose_folder or (lambda: None))


def test_queue_list_responds_on_the_given_sink_only(monkeypatch):
    sent_to_default = []
    monkeypatch.setattr(
        "ytdlx_backend.native_host.handler.send_message",
        lambda msg, stream=None: sent_to_default.append(msg),
    )

    handler = _handler()
    received = []
    handler.handle({"type": "queue.list"}, respond=received.append)

    assert len(received) == 1
    assert received[0]["type"] == "queue.snapshot"
    assert sent_to_default == []


def test_queue_list_falls_back_to_send_message_when_no_sink_given(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "ytdlx_backend.native_host.handler.send_message",
        lambda msg, stream=None: sent.append(msg),
    )

    handler = _handler()
    handler.handle({"type": "queue.list"})

    assert len(sent) == 1
    assert sent[0]["type"] == "queue.snapshot"


def test_progress_routes_to_the_sink_registered_for_that_requestId():
    handler = _handler()
    sink_a, sink_b = [], []
    # Simulates two in-flight requests, each waiting on its own connection
    # (e.g. one direct, one forwarded) -- registered the same way
    # _handle_download_request does internally.
    handler._sinks["req-a"] = sink_a.append
    handler._sinks["req-b"] = sink_b.append

    handler._send_progress(
        QueueItem(request_id="req-a", url="u", page_title="t", status="downloading", percent="10%")
    )
    handler._send_progress(
        QueueItem(request_id="req-b", url="u", page_title="t", status="downloading", percent="20%")
    )

    assert sink_a == [
        {"type": "download.progress", "requestId": "req-a", "percent": "10%", "speed": "", "eta": ""}
    ]
    assert sink_b == [
        {"type": "download.progress", "requestId": "req-b", "percent": "20%", "speed": "", "eta": ""}
    ]


def test_progress_for_an_unregistered_requestId_falls_back_to_send_message(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "ytdlx_backend.native_host.handler.send_message",
        lambda msg, stream=None: sent.append(msg),
    )
    handler = _handler()

    handler._send_progress(
        QueueItem(request_id="unknown", url="u", page_title="t", status="downloading", percent="5%")
    )

    assert len(sent) == 1
    assert sent[0]["requestId"] == "unknown"


def test_complete_releases_the_sink_so_it_is_not_reused():
    handler = _handler()
    messages = []
    handler._sinks["req-a"] = messages.append

    handler._send_progress(
        QueueItem(request_id="req-a", url="u", page_title="t", status="complete", file_path="/x.mp4")
    )

    assert messages == [{"type": "download.complete", "requestId": "req-a", "filePath": "/x.mp4"}]
    assert "req-a" not in handler._sinks


def test_error_releases_the_sink_so_it_is_not_reused():
    handler = _handler()
    messages = []
    handler._sinks["req-a"] = messages.append

    handler._send_progress(
        QueueItem(request_id="req-a", url="u", page_title="t", status="error", error_message="boom")
    )

    assert messages == [{"type": "download.error", "requestId": "req-a", "message": "download failed"}]
    assert "req-a" not in handler._sinks


def test_cancelled_folder_picker_responds_on_the_given_sink_and_never_queues():
    # choose_folder returning None simulates the user cancelling the
    # native folder-picker dialog.
    handler = _handler(choose_folder=lambda: None)
    received = []

    handler.handle(
        {"type": "download.request", "url": "https://example.com/v", "pageTitle": "t", "requestId": "req-a"},
        respond=received.append,
    )

    assert received == [{"type": "download.error", "requestId": "req-a", "message": "cancelled"}]
    assert "req-a" not in handler._sinks
    assert handler._queue.snapshot() == []


def test_invalid_request_responds_on_the_given_sink():
    handler = _handler()
    received = []

    handler.handle({"type": "download.request", "url": "", "pageTitle": "t", "requestId": "req-a"}, respond=received.append)

    assert received == [{"type": "download.error", "requestId": "req-a", "message": "invalid request"}]


def test_has_active_downloads_reflects_queue_state():
    handler = _handler()
    assert handler.has_active_downloads() is False

    with handler._queue._lock:
        handler._queue._items["req-a"] = QueueItem(request_id="req-a", url="u", page_title="t", status="downloading")
    assert handler.has_active_downloads() is True


def test_on_settled_fires_after_a_cancelled_download_with_nothing_else_active():
    # choose_folder returning None simulates the user cancelling the
    # folder picker -- a terminal outcome that never touches the queue at
    # all, so it must still count as "settled".
    settled = []
    handler = RequestHandler(choose_folder=lambda: None, on_settled=lambda: settled.append(True))

    handler.handle({"type": "download.request", "url": "u", "pageTitle": "t", "requestId": "req-a"})

    assert settled == [True]


def test_on_settled_fires_after_an_invalid_request():
    settled = []
    handler = RequestHandler(choose_folder=lambda: None, on_settled=lambda: settled.append(True))

    handler.handle({"type": "download.request", "url": "", "pageTitle": "t", "requestId": "req-a"})

    assert settled == [True]


def test_on_settled_fires_after_complete_when_nothing_else_is_active():
    settled = []
    handler = RequestHandler(choose_folder=lambda: None, on_settled=lambda: settled.append(True))

    handler._send_progress(
        QueueItem(request_id="req-a", url="u", page_title="t", status="complete", file_path="/x.mp4")
    )

    assert settled == [True]


def test_on_settled_fires_after_error_when_nothing_else_is_active():
    settled = []
    handler = RequestHandler(choose_folder=lambda: None, on_settled=lambda: settled.append(True))

    handler._send_progress(
        QueueItem(request_id="req-a", url="u", page_title="t", status="error", error_message="boom")
    )

    assert settled == [True]


def test_on_settled_does_not_fire_while_another_request_is_still_active():
    # Simulates a second, still-downloading request (as start_download
    # would create) without spawning a real download thread.
    settled = []
    handler = RequestHandler(choose_folder=lambda: None, on_settled=lambda: settled.append(True))
    with handler._queue._lock:
        handler._queue._items["req-b"] = QueueItem(request_id="req-b", url="u", page_title="t", status="downloading")

    handler._send_progress(
        QueueItem(request_id="req-a", url="u", page_title="t", status="complete", file_path="/x.mp4")
    )

    assert settled == []
    assert handler.has_active_downloads() is True


def test_on_settled_is_never_called_when_not_given():
    # Just confirms the default (None) doesn't raise -- most callers
    # (e.g. the stdio path in a forwarder-less run) don't care about this.
    handler = _handler()
    handler._send_progress(
        QueueItem(request_id="req-a", url="u", page_title="t", status="complete", file_path="/x.mp4")
    )
