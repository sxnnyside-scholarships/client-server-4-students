"""
Communication Protocol
──────────────────────
Defines the simple text-based protocol used between client and server.

    ┌──────────────────────────────────────────────────────────┐
    │  Every message is a single UTF-8 line:                   │
    │    COMMAND|param1|param2|…\\n                             │
    │                                                          │
    │  File data is sent as raw bytes immediately after the    │
    │  header that announces its size.                         │
    └──────────────────────────────────────────────────────────┘

This protocol is **intentionally simple** for educational purposes.
"""

# ── constants ─────────────────────────────────────────────────

SEPARATOR = "|"
ENCODING = "utf-8"
BUFFER_SIZE = 4096

# Commands (client → server)
CMD_AUTH = "AUTH"            # AUTH|username|password
CMD_LIST = "LIST"            # LIST  or  LIST|subpath
CMD_UPLOAD = "UPLOAD"        # UPLOAD|filename|size
CMD_DOWNLOAD = "DOWNLOAD"    # DOWNLOAD|filename
CMD_MKDIR = "MKDIR"          # MKDIR|dirname
CMD_QUIT = "QUIT"            # QUIT

# Response statuses (server → client)
STATUS_OK = "OK"
STATUS_ERROR = "ERROR"

# Sub-statuses
READY = "READY"
DONE = "DONE"
AUTH_OK = "AUTH_OK"
AUTH_FAIL = "AUTH_FAIL"
GOODBYE = "GOODBYE"


# ── handler ───────────────────────────────────────────────────

class ProtocolHandler:
    """Send and receive protocol messages over a TCP socket.

    Internally keeps a byte buffer so that messages split across
    multiple ``recv()`` calls are reassembled correctly.
    """

    def __init__(self, sock):
        self.sock = sock
        self._buffer = b""

    # ── high-level API ────────────────────────────────────────

    def send_message(self, *parts):
        """Send a protocol line.  Parts are joined with ``|``.

        Example::

            handler.send_message("OK", "READY")   # sends  OK|READY\\n
        """
        line = SEPARATOR.join(str(p) for p in parts) + "\n"
        self.sock.sendall(line.encode(ENCODING))

    def recv_message(self) -> list[str]:
        """Receive one protocol line and split it into parts.

        Example::

            parts = handler.recv_message()  # ["OK", "READY"]
        """
        return self._recv_line().split(SEPARATOR)

    def send_bytes(self, data: bytes):
        """Send raw bytes (used during file transfers)."""
        self.sock.sendall(data)

    def recv_exact(self, size: int) -> bytes:
        """Receive exactly *size* bytes (used during file transfers)."""
        while len(self._buffer) < size:
            chunk = self.sock.recv(BUFFER_SIZE)
            if not chunk:
                raise ConnectionError("Connection closed unexpectedly")
            self._buffer += chunk
        data, self._buffer = self._buffer[:size], self._buffer[size:]
        return data

    # ── internal ──────────────────────────────────────────────

    def _recv_line(self) -> str:
        """Receive bytes until a newline character is found."""
        while b"\n" not in self._buffer:
            chunk = self.sock.recv(BUFFER_SIZE)
            if not chunk:
                raise ConnectionError("Connection closed unexpectedly")
            self._buffer += chunk
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line.decode(ENCODING)
