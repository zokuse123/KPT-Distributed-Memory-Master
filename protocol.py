"""Length-prefixed JSON protocol used by the Master and Worker."""

from __future__ import annotations

import json
import socket
import struct
from typing import Any

HEADER_SIZE = 4
MAX_MESSAGE_SIZE = 1_048_576  # 1 MiB is ample for the small protocol messages.


class ProtocolError(Exception):
    """Raised when a peer sends an invalid or incomplete protocol message."""


def recv_exact(sock: socket.socket, size: int) -> bytes:
    """Receive exactly *size* bytes or raise ProtocolError on early EOF."""
    if size < 0:
        raise ValueError("size must not be negative")
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise ProtocolError(
                f"connection closed after {len(chunks)} of {size} expected bytes"
            )
        chunks.extend(chunk)
    return bytes(chunks)


def send_message(sock: socket.socket, message: dict[str, Any]) -> None:
    """Serialize and send one UTF-8 JSON message with a big-endian length."""
    try:
        payload = json.dumps(
            message, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"message is not JSON serializable: {exc}") from exc
    if not payload or len(payload) > MAX_MESSAGE_SIZE:
        raise ProtocolError(f"invalid outgoing message length: {len(payload)} bytes")
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def receive_message(sock: socket.socket) -> dict[str, Any]:
    """Receive, decode, and return one framed JSON object."""
    (length,) = struct.unpack("!I", recv_exact(sock, HEADER_SIZE))
    if length == 0 or length > MAX_MESSAGE_SIZE:
        raise ProtocolError(f"invalid incoming message length: {length} bytes")
    payload = recv_exact(sock, length)
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"invalid UTF-8 JSON payload: {exc}") from exc
    if not isinstance(message, dict):
        raise ProtocolError("JSON message must be an object")
    return message


def make_task(task_id: str, start: int, end: int) -> dict[str, Any]:
    return {"type": "TASK", "task_id": task_id, "start": start, "end": end}


def validate_result(
    message: dict[str, Any], *, task_id: str, start: int, end: int
) -> tuple[int, float]:
    """Validate a RESULT against its TASK and return count and worker time."""
    if message.get("type") != "RESULT":
        raise ProtocolError(f"expected RESULT, received {message.get('type')!r}")
    for field, expected in (("task_id", task_id), ("start", start), ("end", end)):
        if message.get(field) != expected:
            raise ProtocolError(
                f"RESULT {field} mismatch: expected {expected!r}, "
                f"received {message.get(field)!r}"
            )

    count = message.get("prime_count")
    if isinstance(count, bool) or not isinstance(count, int):
        raise ProtocolError("RESULT prime_count must be an integer")
    interval_size = max(0, end - start + 1)
    if count < 0 or count > interval_size:
        raise ProtocolError("RESULT prime_count is outside the valid range")

    worker_seconds = message.get("compute_seconds")
    if (
        isinstance(worker_seconds, bool)
        or not isinstance(worker_seconds, (int, float))
        or worker_seconds < 0
    ):
        raise ProtocolError("RESULT compute_seconds must be a non-negative number")
    return count, float(worker_seconds)

