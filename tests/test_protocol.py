import json
import socket
import struct
import threading
import unittest

from protocol import ProtocolError, receive_message, recv_exact, send_message, validate_result


class ProtocolTests(unittest.TestCase):
    def test_recv_exact_handles_partial_reads(self):
        receiver, sender = socket.socketpair()
        try:
            def write_chunks():
                for chunk in (b"ab", b"c", b"def"):
                    sender.sendall(chunk)

            thread = threading.Thread(target=write_chunks)
            thread.start()
            self.assertEqual(recv_exact(receiver, 6), b"abcdef")
            thread.join()
        finally:
            receiver.close()
            sender.close()

    def test_multiple_messages_on_one_connection(self):
        left, right = socket.socketpair()
        messages = [
            {"type": "TASK", "task_id": "run-001", "start": 5, "end": 10},
            {"type": "TASK", "task_id": "run-002", "start": 11, "end": 20},
        ]
        try:
            for message in messages:
                send_message(left, message)
            self.assertEqual(receive_message(right), messages[0])
            self.assertEqual(receive_message(right), messages[1])
        finally:
            left.close()
            right.close()

    def test_rejects_oversized_declared_frame(self):
        left, right = socket.socketpair()
        try:
            left.sendall(struct.pack("!I", 1_048_577))
            with self.assertRaises(ProtocolError):
                receive_message(right)
        finally:
            left.close()
            right.close()

    def test_validate_result(self):
        message = {
            "type": "RESULT", "task_id": "run-001", "start": 5, "end": 10,
            "prime_count": 2, "compute_seconds": 0.01,
        }
        self.assertEqual(
            validate_result(message, task_id="run-001", start=5, end=10),
            (2, 0.01),
        )
        bad = json.loads(json.dumps(message))
        bad["task_id"] = "wrong"
        with self.assertRaises(ProtocolError):
            validate_result(bad, task_id="run-001", start=5, end=10)


if __name__ == "__main__":
    unittest.main()

