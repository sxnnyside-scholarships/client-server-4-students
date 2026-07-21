"""
Module: engine.py
─────────────────
Purpose: Manages outbound TCP connections and raw socket operations.

Architectural Role:
This is the foundational layer of the client network stack. It abstracts away
Python's standard `socket` library, providing a callback-based interface that
upper layers (`operations.py`, `transfers.py`) can use to communicate without
writing raw byte arrays.

Responsibilities:
- Establish TCP sockets and manage connection retries.
- Perform the CS4S protocol handshake and capability negotiation.
- Perform user authentication over the wire.
- Maintain thread synchronization primitives (Locks, Events).

Expected Collaborators:
- `src.network.client_backend` (consumes engine callbacks).
- `src.core.protocol.ProtocolHandler` (wraps the raw socket).
"""

import socket
import threading
from typing import Callable

from src.core.protocol import (
    CMD_AUTH,
    CMD_HELLO,
    CMD_QUIT,
    CODE_AUTH_OK,
    CODE_GREETING,
    PROTOCOL_VERSION,
    ProtocolHandler,
)
from src.network.errors import NetworkError, map_socket_error


class ClientConnectionEngine:
    """
    Manages socket lifecycle, connection state, and synchronization locks.

    Why it exists:
    Raw socket operations block the thread they run on. This engine isolates that
    complexity into a background thread, ensuring the GUI remains responsive while
    connecting, authenticating, or failing.

    Responsibilities:
    - Executing connection attempts asynchronously.
    - Emitting callbacks when the state changes (connected, auth failed, error).
    - Providing `threading.Lock` access for thread-safe socket writes.

    Non-Responsibilities (Anti-Goals):
    - It does NOT parse incoming file directory listings (delegated to Operations).
    - It does NOT stream binary file data (delegated to Transfers).
    """

    def __init__(self):
        self._socket: socket.socket | None = None
        self._proto: ProtocolHandler | None = None
        self._connected = False
        self._lock = threading.Lock()
        self._transfers_lock = threading.Lock()
        self._active_transfers: dict[str, threading.Event] = {}
        self._shutdown_event = threading.Event()

        self.enable_tls = False

        # Callbacks
        self.on_connected: Callable[[], None] = lambda: None
        self.on_disconnected: Callable[[], None] = lambda: None
        self.on_auth_success: Callable[[], None] = lambda: None
        self.on_auth_failed: Callable[[str], None] = lambda x: None
        self.on_error_occurred: Callable[[str, str], None] = lambda x, y: None
        self.on_connection_recovering: Callable[[int, int], None] = lambda x, y: None
        self.on_status_message: Callable[[str], None] = lambda x: None
        self.on_capabilities_discovered: Callable[[list], None] = lambda x: None

        self.on_packet_tx: Callable[[str], None] = lambda x: None
        self.on_packet_rx: Callable[[str], None] = lambda x: None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def proto(self) -> ProtocolHandler | None:
        return self._proto

    @property
    def shutdown_event(self) -> threading.Event:
        return self._shutdown_event

    @property
    def lock(self) -> threading.Lock:
        return self._lock

    @property
    def transfers_lock(self) -> threading.Lock:
        return self._transfers_lock

    @property
    def active_transfers(self) -> dict[str, threading.Event]:
        return self._active_transfers

    def run_in_background(self, fn, *args):
        """
        Executes a target function in a detached daemon thread.

        Args:
            fn: The target callable.
            *args: Arguments to pass to the callable.

        Returns:
            None.

        Side Effects:
            Spawns a new OS thread.

        Failure Behavior:
            If the thread crashes, it dies silently without taking down the main app.
        """
        threading.Thread(target=fn, args=args, daemon=True).start()

    def fail_disconnected(self):
        """
        Forces the internal state to disconnected and fires callbacks.

        Args:
            None.

        Returns:
            None.

        Side Effects:
            Mutates `_connected` to False.
            Invokes `on_disconnected()`.

        Failure Behavior:
            None.
        """
        self._connected = False
        self.on_disconnected()

    def connect(self, host: str, port: int, user: str, pwd: str):
        """
        Asynchronously initiates a connection sequence.

        Args:
            host: The remote IP or hostname.
            port: The remote TCP port.
            user: The username.
            pwd: The plaintext password.

        Returns:
            None.

        Side Effects:
            Spawns a background thread running `_do_connect`.

        Failure Behavior:
            None (handled within the thread).
        """
        self.run_in_background(self._do_connect, host, port, user, pwd)

    def _do_connect(self, host: str, port: int, user: str, pwd: str):
        self._shutdown_event.clear()
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            if self._shutdown_event.is_set():
                return
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((host, port))

                if self.enable_tls:
                    import ssl

                    # Use unverified context for educational self-signed certificates
                    context = ssl._create_unverified_context()
                    sock = context.wrap_socket(sock, server_hostname=host)

                self._socket = sock
                self._proto = ProtocolHandler(sock, on_tx=self.on_packet_tx, on_rx=self.on_packet_rx)
                if self.enable_tls:
                    self._proto.is_tls = True

                self._connected = True

                # Protocol Handshake
                self._socket.settimeout(5.0)
                self._proto.send_message(CMD_HELLO, PROTOCOL_VERSION)
                resp = self._proto.recv_message()

                if resp[0] != str(CODE_GREETING):
                    err_msg = resp[2] if len(resp) > 2 else "Version mismatch"
                    self.on_error_occurred(NetworkError.PROTOCOL_ERROR.value, err_msg)
                    self._connected = False
                    self.on_disconnected()
                    return

                # Parse capabilities
                caps = []
                for part in resp[3:]:
                    if part.startswith("CAPS:"):
                        caps = part.split(":")[1].split(",")
                if caps:
                    self.on_capabilities_discovered(caps)

                # Authenticate
                self._proto.send_message(CMD_AUTH, user, pwd)
                resp = self._proto.recv_message()

                if resp[0] == str(CODE_AUTH_OK):
                    self._socket.settimeout(30.0)
                    self.on_connected()
                    self.on_auth_success()
                    self.on_status_message(f"Authenticated as {user}")
                    return
                else:
                    reason = resp[2] if len(resp) > 2 else "Unknown error"
                    self.on_auth_failed(reason)
                    self.disconnect()
                    return
            except (ConnectionRefusedError, ConnectionError, OSError) as exc:
                if self._socket:
                    try:
                        self._socket.close()
                    except OSError:
                        pass
                if self._shutdown_event.is_set():
                    return
                if attempt < max_attempts:
                    self.on_connection_recovering(attempt, max_attempts)
                    import time

                    time.sleep(attempt)
                else:
                    err_code = map_socket_error(exc).value
                    self.on_error_occurred(err_code, f"Connection failed: {exc}")
                    self._connected = False
                    self.on_disconnected()

    def disconnect(self):
        """
        Gracefully terminates the connection and shuts down threads.

        Args:
            None.

        Returns:
            None.

        Side Effects:
            Sets the shutdown event.
            Attempts to send a `QUIT` protocol message cleanly before closing the socket.
            Invokes `on_disconnected()`.

        Failure Behavior:
            If the socket lock cannot be acquired, forces the socket closed anyway.
        """
        if not self._connected:
            return

        self._connected = False
        self._shutdown_event.set()

        try:
            if self._lock.acquire(timeout=2.0):
                try:
                    if self._proto and self._socket:
                        self._socket.settimeout(2.0)
                        self._proto.send_message(CMD_QUIT)
                except (OSError, ConnectionError):
                    pass
                finally:
                    if self._socket:
                        try:
                            self._socket.close()
                        except OSError:
                            pass
                    self._lock.release()
            else:
                if self._socket:
                    try:
                        self._socket.close()
                    except OSError:
                        pass
        finally:
            self.on_disconnected()
            self.on_status_message("Disconnected")
