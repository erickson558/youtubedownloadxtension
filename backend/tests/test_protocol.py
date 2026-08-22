import io
import json
import struct

import pytest

from ytdlx_backend.native_host.protocol import (
    MAX_MESSAGE_BYTES,
    MessageTooLargeError,
    read_message,
    send_message,
)


def test_round_trip():
    stream = io.BytesIO()
    send_message({"type": "download.progress", "requestId": "abc", "percent": "50%"}, stream=stream)
    stream.seek(0)
    assert read_message(stream) == {"type": "download.progress", "requestId": "abc", "percent": "50%"}


def test_read_message_returns_none_on_empty_stream():
    assert read_message(io.BytesIO(b"")) is None


def test_read_message_returns_none_on_truncated_body():
    # A length prefix claiming more bytes than are actually present.
    stream = io.BytesIO(struct.pack("<I", 100) + b"short")
    assert read_message(stream) is None


def test_read_message_rejects_oversized_length_prefix_without_reading_body():
    # The declared length exceeds the cap; this must raise *before*
    # attempting to read MAX_MESSAGE_BYTES + 1 bytes (specs/03-security-spec.md rule 4).
    stream = io.BytesIO(struct.pack("<I", MAX_MESSAGE_BYTES + 1))
    with pytest.raises(MessageTooLargeError):
        read_message(stream)


def test_send_message_rejects_oversized_payload():
    huge_payload = {"data": "x" * (MAX_MESSAGE_BYTES + 1)}
    with pytest.raises(MessageTooLargeError):
        send_message(huge_payload, stream=io.BytesIO())


def test_wire_format_matches_spec():
    stream = io.BytesIO()
    send_message({"a": 1}, stream=stream)
    raw = stream.getvalue()
    (length,) = struct.unpack("<I", raw[:4])
    assert json.loads(raw[4 : 4 + length].decode("utf-8")) == {"a": 1}
