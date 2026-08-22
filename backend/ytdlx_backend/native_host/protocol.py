"""WebExtensions native-messaging stdio framing.

Wire format (identical for Chrome and Firefox, see
specs/02-native-host-spec.md): each message is a 4-byte little-endian
unsigned length prefix, followed by that many bytes of UTF-8 JSON.

The 1 MiB cap below is enforced *before* reading the body, not after —
per specs/03-security-spec.md rule 4, this defends against a malformed or
hostile length prefix causing an unbounded read into memory.
"""

from __future__ import annotations

import json
import struct
import sys
import threading
from typing import Any, BinaryIO

MAX_MESSAGE_BYTES = 1024 * 1024  # 1 MiB; the conservative cross-browser limit

# Multiple downloads run on separate threads (see downloader/queue_manager.py)
# and each can call send_message() concurrently; without serializing the two
# writes (length prefix, then body) below, two interleaved messages would
# corrupt the framing for both. One lock per process is sufficient since
# stdout itself is a single, process-wide stream.
_write_lock = threading.Lock()


class MessageTooLargeError(ValueError):
    """Raised when a peer claims a message body larger than MAX_MESSAGE_BYTES."""


def read_message(stream: BinaryIO | None = None) -> dict[str, Any] | None:
    """Reads one framed message from `stream` (defaults to stdin).

    Returns None when the stream is closed (the browser disconnected the
    native host), which callers should treat as "exit cleanly".
    """
    stream = stream if stream is not None else sys.stdin.buffer

    raw_length = stream.read(4)
    if not raw_length or len(raw_length) < 4:
        return None

    (length,) = struct.unpack("<I", raw_length)
    if length > MAX_MESSAGE_BYTES:
        # Do not attempt to read `length` bytes — that's the exact
        # unbounded-read this check exists to prevent.
        raise MessageTooLargeError(
            f"declared message length {length} exceeds {MAX_MESSAGE_BYTES} byte cap"
        )

    body = stream.read(length)
    if len(body) < length:
        return None  # stream closed mid-message

    return json.loads(body.decode("utf-8"))


def send_message(message: dict[str, Any], stream: BinaryIO | None = None) -> None:
    """Writes one framed message to `stream` (defaults to stdout)."""
    stream = stream if stream is not None else sys.stdout.buffer

    data = json.dumps(message).encode("utf-8")
    if len(data) > MAX_MESSAGE_BYTES:
        raise MessageTooLargeError(
            f"outgoing message of {len(data)} bytes exceeds {MAX_MESSAGE_BYTES} byte cap"
        )

    with _write_lock:
        stream.write(struct.pack("<I", len(data)))
        stream.write(data)
        stream.flush()
