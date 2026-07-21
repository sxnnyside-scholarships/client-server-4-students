"""
Module: operations.py
─────────────────────
Purpose: Executes fast, synchronous client-server commands (LIST, MKDIR, DELETE).

Architectural Role:
Acts as the Remote Procedure Call (RPC) layer for the client. It handles operations
that are expected to return immediately, utilizing the connection lock to prevent
command collision on the shared TCP socket.

Responsibilities:
- Serialize file management intents (rename, move, delete) into protocol commands.
- Parse structured responses (like directory listings) back into Python dictionaries.
- Ensure all socket writing is thread-safe using the engine lock.

Expected Collaborators:
- `src.network.client.engine` (provides the raw socket and lock).
- `src.network.client_backend` (exposes these operations to the UI).
"""

import time
from typing import Callable

from src.core.protocol import (
    CMD_LIST,
    CMD_MKDIR,
    CMD_PING,
    CODE_ACTION_OK,
    CODE_OK,
)
from src.network.errors import NetworkError, map_socket_error


class ClientOperations:
    """
    Handles standard fast, synchronous command-response pairs.

    Why it exists:
    Separating these quick operations from slow file transfers (`transfers.py`)
    prevents the codebase from becoming a tangled "god object" of commands.
    It ensures the UI can list directories cleanly without worrying about threading.

    Responsibilities:
    - Structuring payload arguments for `CMD_LIST`, `CMD_MKDIR`, etc.
    - Emitting success or failure callbacks.

    Non-Responsibilities (Anti-Goals):
    - It does NOT transfer binary file payloads.
    - It does NOT attempt to reconnect if the socket drops.
    """

    def __init__(self, engine):
        self.engine = engine

        # Callbacks
        self.on_file_list_received: Callable[[list], None] = lambda x: None
        self.on_directory_created: Callable[[], None] = lambda: None
        self.on_action_completed: Callable[[str], None] = lambda x: None
        self.on_rtt_measured: Callable[[float], None] = lambda x: None

    def list_files(self, path: str = ""):
        """
        Asynchronously requests a directory listing from the server.

        Args:
            path: The relative directory path to list.

        Returns:
            None.

        Side Effects:
            Spawns a background thread running `_do_list`.

        Failure Behavior:
            None (handled in background).
        """
        self.engine.run_in_background(self._do_list, path)

    def _do_list(self, path):
        with self.engine.lock:
            if not self.engine.is_connected or not self.engine.proto or self.engine.shutdown_event.is_set():
                self.engine.on_error_occurred(NetworkError.CONNECTION_LOST.value, "Not connected")
                return
            try:
                self.engine.proto.send_message(CMD_LIST, path)
                resp = self.engine.proto.recv_message()
                if resp[0] == str(CODE_OK):
                    entries = []
                    raw = resp[2] if len(resp) > 2 else ""
                    if raw:
                        for tok in raw.split(";"):
                            parts = tok.split(":")
                            if len(parts) == 3:
                                entries.append(
                                    {
                                        "name": parts[0],
                                        "size": int(parts[1]),
                                        "type": parts[2],
                                    }
                                )
                    self.on_file_list_received(entries)
                else:
                    err = resp[2] if len(resp) > 2 else "Unknown"
                    self.engine.on_error_occurred(NetworkError.PROTOCOL_ERROR.value, f"List failed: {err}")
            except (ConnectionError, OSError) as exc:
                self.engine.on_error_occurred(map_socket_error(exc).value, f"Connection error: {exc}")
                self.engine.fail_disconnected()

    def create_directory(self, dirname: str):
        """
        Asynchronously requests the server to create a new folder.

        Args:
            dirname: The new folder name.

        Returns:
            None.

        Side Effects:
            Spawns a background thread running `_do_mkdir`.

        Failure Behavior:
            None.
        """
        self.engine.run_in_background(self._do_mkdir, dirname)

    def _do_mkdir(self, dirname):
        with self.engine.lock:
            if not self.engine.is_connected or not self.engine.proto or self.engine.shutdown_event.is_set():
                self.engine.on_error_occurred(NetworkError.CONNECTION_LOST.value, "Not connected")
                return
            try:
                self.engine.proto.set_timeout(30.0)
                self.engine.proto.send_message(CMD_MKDIR, dirname)
                resp = self.engine.proto.recv_message()
                if resp[0] == str(CODE_ACTION_OK):
                    self.engine.on_status_message(f"Created folder: {dirname}")
                    self.on_directory_created()
                else:
                    err = resp[2] if len(resp) > 2 else "Failed"
                    self.engine.on_error_occurred(NetworkError.PROTOCOL_ERROR.value, f"Mkdir failed: {err}")
            except (ConnectionError, OSError) as exc:
                self.engine.on_error_occurred(map_socket_error(exc).value, f"Error: {exc}")
                self.engine.fail_disconnected()

    def ping(self):
        """
        Asynchronously measures round-trip latency to the server.

        Args:
            None.

        Returns:
            None.

        Side Effects:
            Spawns a background thread running `_do_ping`.

        Failure Behavior:
            None (handled in background).
        """
        self.engine.run_in_background(self._do_ping)

    def _do_ping(self):
        with self.engine.lock:
            if not self.engine.is_connected or not self.engine.proto or self.engine.shutdown_event.is_set():
                return
            try:
                self.engine.proto.set_timeout(5.0)
                start = time.perf_counter()
                self.engine.proto.send_message(CMD_PING)
                self.engine.proto.recv_message()
                rtt_ms = (time.perf_counter() - start) * 1000.0
                self.on_rtt_measured(rtt_ms)
            except (ConnectionError, OSError):
                # A failed latency probe isn't a fatal error worth surfacing
                # to the user — the next probe will simply retry.
                pass

    def do_action(self, cmd: str, *args):
        """
        Generic runner for fast commands like DELETE, RENAME, and MOVE.

        Args:
            cmd: The protocol command string.
            *args: Variable arguments corresponding to the command payload.

        Returns:
            None.

        Side Effects:
            Spawns a background thread.

        Failure Behavior:
            None.
        """
        self.engine.run_in_background(self._do_action_bg, cmd, *args)

    def _do_action_bg(self, cmd: str, *args):
        with self.engine.lock:
            if not self.engine.is_connected or not self.engine.proto or self.engine.shutdown_event.is_set():
                self.engine.on_error_occurred(NetworkError.CONNECTION_LOST.value, "Not connected")
                return
            try:
                self.engine.proto.set_timeout(30.0)
                self.engine.proto.send_message(cmd, *args)
                resp = self.engine.proto.recv_message()
                if resp[0] == str(CODE_ACTION_OK):
                    self.on_action_completed(cmd)
                else:
                    err = resp[2] if len(resp) > 2 else "Failed"
                    self.engine.on_error_occurred(NetworkError.PROTOCOL_ERROR.value, f"{cmd} failed: {err}")
            except (ConnectionError, OSError) as exc:
                self.engine.on_error_occurred(map_socket_error(exc).value, f"Error: {exc}")
                self.engine.fail_disconnected()

    def send_raw(self, raw_cmd: str):
        """
        Injects a raw protocol string into the socket for educational Lab View.

        Args:
            raw_cmd: The unvalidated string command.

        Returns:
            None.

        Side Effects:
            Spawns a background thread running `_do_send_raw`.

        Failure Behavior:
            None.
        """
        self.engine.run_in_background(self._do_send_raw, raw_cmd)

    def _do_send_raw(self, raw_cmd: str):
        with self.engine.lock:
            if not self.engine.is_connected or not self.engine.proto or self.engine.shutdown_event.is_set():
                self.engine.on_error_occurred(NetworkError.CONNECTION_LOST.value, "Not connected")
                return
            try:
                self.engine.proto.set_timeout(30.0)
                parts = raw_cmd.strip().split("|")
                self.engine.proto.send_message(*parts)
                self.engine.proto.recv_message()
            except (ConnectionError, OSError) as exc:
                self.engine.on_error_occurred(map_socket_error(exc).value, f"Error: {exc}")
                self.engine.fail_disconnected()
