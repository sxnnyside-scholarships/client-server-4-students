"""
Module: protocol.py
───────────────────
Purpose: Defines the text-based application protocol and standardizes socket read/write operations.

Architectural Role:
Acts as the boundary between abstract application requests (e.g., "list files") and
raw TCP socket bytes. It enforces the framing format required for the client and server
to safely exchange variable-length streams.

Responsibilities:
- Provide all standardized protocol constants (Commands and Response Codes).
- Provide a `ProtocolHandler` that wraps a raw Python socket.
- Handle byte buffering to solve TCP stream fragmentation.

Expected Collaborators:
- `src.network.client.engine`
- `src.network.server.connection`

Important Implementation Notes:
    ┌──────────────────────────────────────────────────────────┐
    │  Every message is a single UTF-8 line:                   │
    │    COMMAND|param1|param2|…\\n                             │
    │                                                          │
    │  File data is sent as raw bytes immediately after the    │
    │  header that announces its size.                         │
    └──────────────────────────────────────────────────────────┘

This protocol is **intentionally simple** for educational purposes, heavily relying
on newline framing (`\\n`) for command barriers.
"""

# ── constants ─────────────────────────────────────────────────

SEPARATOR = "|"
ENCODING = "utf-8"
BUFFER_SIZE = 4096

# Commands (client → server)
CMD_HELLO = "HELLO"  # HELLO|CS4S/2.0
CMD_AUTH = "AUTH"  # AUTH|username|password
CMD_LIST = "LIST"  # LIST  or  LIST|subpath
CMD_UPLOAD = "UPLOAD"  # UPLOAD|filename|size
CMD_DOWNLOAD = "DOWNLOAD"  # DOWNLOAD|filename
CMD_MKDIR = "MKDIR"  # MKDIR|dirname
CMD_DELETE = "DELETE"  # DELETE|filename
CMD_RENAME = "RENAME"  # RENAME|old_name|new_name
CMD_MOVE = "MOVE"  # MOVE|filename|dest_dir
CMD_QUIT = "QUIT"  # QUIT
CMD_PING = "PING"  # PING (round-trip latency probe)

# Response codes (server → client)
CODE_OK = 200  # Generic Success
CODE_GREETING = 220  # HELLO response
CODE_GOODBYE = 221  # QUIT response
CODE_TRANSFER_DONE = 226  # End of file transfer
CODE_AUTH_OK = 230  # Auth success
CODE_ACTION_OK = 250  # File operation success

CODE_BAD_REQ = 400  # Malformed / Missing HELLO
CODE_UNAUTHORIZED = 401  # Not logged in
CODE_FORBIDDEN = 403  # Permission denied
CODE_NOT_FOUND = 404  # File/Dir not found
CODE_CONFLICT = 409  # File already exists
CODE_AUTH_FAIL = 430  # Bad username/password

CODE_INTERNAL_ERR = 500  # Unexpected exception
CODE_UNAVAILABLE = 503  # Max connections
CODE_VERSION_ERR = 505  # Protocol version mismatch

# Status strings (mapped to details in numeric responses)
STATUS_OK = "OK"
STATUS_ERROR = "ERROR"
READY = "READY"
DONE = "DONE"
AUTH_OK = "AUTH_OK"
AUTH_FAIL = "AUTH_FAIL"
GOODBYE = "GOODBYE"
PROTOCOL_VERSION = "CS4S/2.0"
CAPABILITIES = "CAPS:DELETE,RENAME,MOVE"


# ── handler ───────────────────────────────────────────────────


class ProtocolHandler:
    """
    Send and receive protocol messages over a TCP socket.

    Why it exists:
    Raw TCP sockets stream bytes without boundaries. `ProtocolHandler` solves the
    TCP fragmentation problem by implementing an internal byte buffer, ensuring that
    the application only processes complete messages.

    Responsibilities:
    - Buffering partial byte reads from the socket until a complete `\\n` delimiter is found.
    - Encoding and decoding strings to UTF-8 bytes.
    - Invoking telemetry hooks (`on_tx`, `on_rx`) for the Protocol Inspector UI.

    Non-Responsibilities (Anti-Goals):
    - It does NOT parse or validate the *meaning* of the commands (delegated to Dispatchers).
    - It does NOT manage the connection lifecycle (connect/disconnect/reconnect).
    """

    def __init__(self, sock, on_tx=None, on_rx=None):
        self.sock = sock
        self._buffer = b""
        self.on_tx = on_tx
        self.on_rx = on_rx
        self.bytes_tx = 0
        self.bytes_rx = 0
        self.messages_tx = 0
        self.messages_rx = 0
        self.is_tls = False

    # ── high-level API ────────────────────────────────────────

    def set_timeout(self, seconds: float | None):
        """
        Sets the underlying socket's blocking timeout.

        Args:
            seconds: Timeout in seconds, or None to block indefinitely.

        Returns:
            None.

        Side Effects:
            Mutates the underlying socket's timeout.

        Failure Behavior:
            None.
        """
        self.sock.settimeout(seconds)

    def send_message(self, *parts):
        """
        Formats and sends a single protocol command line.

        Args:
            *parts: Variable length string parts that will be joined by the separator (`|`).

        Returns:
            None.

        Side Effects:
            Appends a newline (`\\n`) and writes bytes directly to the underlying socket.
            Invokes the `on_tx` callback if configured.

        Failure Behavior:
            Raises `OSError` / `socket.error` if the socket is broken or closed.
        """
        line = SEPARATOR.join(str(p) for p in parts)
        if self.on_tx:
            if self.is_tls:
                self.on_tx(f"[Encrypted TLS Record: {len(line)} bytes]")
            else:
                self.on_tx(line)
        encoded = (line + "\n").encode(ENCODING)
        self.sock.sendall(encoded)
        self.bytes_tx += len(encoded)
        self.messages_tx += 1

    def recv_message(self) -> list[str]:
        """
        Reads from the socket until a complete protocol line is received, then parses it.

        Args:
            None.

        Returns:
            A list of strings split by the protocol separator (`|`).

        Side Effects:
            Blocks the current thread until a newline character is received from the socket.
            Mutates the internal byte buffer.

        Failure Behavior:
            Raises `ConnectionError` if the socket closes before a newline is received.
        """
        return self._recv_line().split(SEPARATOR)

    def send_bytes(self, data: bytes):
        """
        Transmits raw unformatted binary data over the socket.

        Args:
            data: The exact byte payload to transmit.

        Returns:
            None.

        Side Effects:
            Writes directly to the socket.

        Failure Behavior:
            Raises `OSError` if the connection drops during transmission.
        """
        self.sock.sendall(data)
        self.bytes_tx += len(data)

    def recv_exact(self, size: int) -> bytes:
        """
        Receives an exact number of bytes from the socket, regardless of delimiters.

        # Educational Note: TCP Fragmentation
        # A single `sock.recv()` is NOT guaranteed to return all requested bytes. It may return
        # a smaller chunk. This loop guarantees we block until exactly `size` bytes are buffered.

        Args:
            size: The exact number of bytes required.

        Returns:
            A byte string of exactly length `size`.

        Side Effects:
            Blocks the current thread until the requested bytes arrive.
            Mutates the internal byte buffer.

        Failure Behavior:
            Raises `ConnectionError` if the socket closes before the target size is reached.
        """
        while len(self._buffer) < size:
            chunk = self.sock.recv(BUFFER_SIZE)
            if not chunk:
                raise ConnectionError("Connection closed unexpectedly")
            self._buffer += chunk
            self.bytes_rx += len(chunk)
        data, self._buffer = self._buffer[:size], self._buffer[size:]
        return data

    # ── internal ──────────────────────────────────────────────

    def _recv_line(self) -> str:
        """
        Internal buffer loop that reads bytes until a newline is found.

        Args:
            None.

        Returns:
            The decoded string payload (excluding the newline character).

        Side Effects:
            Mutates `self._buffer`. Invokes `on_rx` telemetry callback.

        Failure Behavior:
            Raises `ConnectionError` if EOF is reached.
        """
        while b"\n" not in self._buffer:
            chunk = self.sock.recv(BUFFER_SIZE)
            if not chunk:
                raise ConnectionError("Connection closed unexpectedly")
            self._buffer += chunk
            self.bytes_rx += len(chunk)
        line, self._buffer = self._buffer.split(b"\n", 1)
        decoded = line.decode(ENCODING)
        self.messages_rx += 1
        if self.on_rx:
            if self.is_tls:
                self.on_rx(f"[Encrypted TLS Record: {len(decoded)} bytes]")
            else:
                self.on_rx(decoded)
        return decoded
