"""
Module: transfer.py
───────────────────
Purpose: Executes long-running byte streams for UPLOAD and DOWNLOAD commands.

Architectural Role:
Acts as the execution handler for streaming operations. Unlike `file_ops`, these 
methods block the thread while reading/writing megabytes of data in chunks. 
They directly interact with the raw socket bypassing the normal string message protocol.

Responsibilities:
- Parse `CMD_UPLOAD` and `CMD_DOWNLOAD` arguments.
- Safely resolve requested filenames against the user's sandbox directory.
- Perform chunked binary reads and writes over the active socket connection.
- Monitor the `engine._shutdown_event` to abort cleanly on server shutdown.

Expected Collaborators:
- `src.network.server.dispatcher` (invokes these methods).
- `src.storage.file_manager.FileManager` (resolves paths and sizes).
"""

import logging
from src.core.protocol import (
    BUFFER_SIZE,
    CODE_ACTION_OK,
    CODE_BAD_REQ,
    CODE_FORBIDDEN,
    CODE_INTERNAL_ERR,
    CODE_NOT_FOUND,
    CODE_OK,
    DONE,
    ProtocolHandler,
    READY,
    STATUS_ERROR,
    STATUS_OK,
)
from src.storage.file_manager import FileManager

logger = logging.getLogger("server.transfer")

class TransferHandler:
    """
    Executes binary file transfers directly over the protocol socket.

    Why it exists:
    A 1GB file cannot be read into RAM all at once. This handler implements 
    buffered byte streaming to keep memory usage flat, regardless of file size.

    Responsibilities:
    - Managing `BUFFER_SIZE` loops for reads and writes.
    - Synchronizing protocol state before and after binary transmission.

    Non-Responsibilities (Anti-Goals):
    - It does NOT calculate client-side transfer speeds.
    - It does NOT parse standard string commands.
    """

    def __init__(self, file_manager: FileManager):
        self.files = file_manager

    def cmd_upload(self, proto: ProtocolHandler, parts: list, user: str, engine):
        """
        Receives a binary file from the client and saves it to disk.

        Args:
            proto: The client's active protocol handler.
            parts: The parsed string payload (expected: ['UPLOAD', filename, size]).
            user: The authenticated username (sandbox owner).
            engine: The parent server engine (checked for shutdown events).

        Returns:
            None.

        Side Effects:
            Blocks the thread for the duration of the transfer.
            Writes binary data to the local disk.
            Consumes raw bytes directly from the socket buffer.

        Failure Behavior:
            Sends `CODE_BAD_REQ` if arguments are missing or malformed.
            Sends `CODE_FORBIDDEN` if the path escapes the sandbox.
            Sends `CODE_INTERNAL_ERR` if disk I/O fails mid-transfer.
        """
        if len(parts) < 3:
            proto.send_message(CODE_BAD_REQ, STATUS_ERROR, "Missing arguments")
            return
        filename = parts[1]
        try:
            size = int(parts[2])
        except ValueError:
            proto.send_message(CODE_BAD_REQ, STATUS_ERROR, "Invalid size")
            return

        target_path = self.files.get_file_path(user, filename)
        if target_path is None:
            proto.send_message(CODE_FORBIDDEN, STATUS_ERROR, "Path traversal rejected")
            return

        proto.send_message(CODE_OK, STATUS_OK, READY)
        received = 0
        addr = getattr(proto, "client_addr", None)
        if addr:
            engine.on_socket_state_changed(addr, "TRANSFERRING")
        try:
            with open(target_path, "wb") as fh:
                while received < size:
                    # In ServerNetworkEngine, we check engine._shutdown_event
                    if getattr(engine, '_shutdown_event').is_set():
                        raise ConnectionAbortedError("Server shutting down")
                    want = min(BUFFER_SIZE, size - received)
                    chunk = proto.recv_exact(want)
                    fh.write(chunk)
                    received += len(chunk)
            proto.send_message(CODE_ACTION_OK, STATUS_OK, DONE)
            engine.on_log_message(f"Received file '{filename}' from {user}")
        except Exception as exc:
            logger.error("Upload error: %s", exc)
            proto.send_message(CODE_INTERNAL_ERR, STATUS_ERROR, "Transfer failed")
        finally:
            if addr:
                engine.on_socket_state_changed(addr, "IDLE")

    def cmd_download(self, proto: ProtocolHandler, parts: list, user: str, engine):
        """
        Reads a binary file from disk and streams it to the client.

        Args:
            proto: The client's active protocol handler.
            parts: The parsed string payload (expected: ['DOWNLOAD', filename]).
            user: The authenticated username.
            engine: The parent server engine.

        Returns:
            None.

        Side Effects:
            Blocks the thread for the duration of the transfer.
            Reads binary data from the local disk.
            Writes raw bytes directly to the socket buffer.

        Failure Behavior:
            Sends `CODE_BAD_REQ` if the filename is missing.
            Sends `CODE_FORBIDDEN` if the path escapes the sandbox.
            Sends `CODE_NOT_FOUND` if the file doesn't exist.
            Silently stops streaming if the client disconnects.
        """
        if len(parts) < 2:
            proto.send_message(CODE_BAD_REQ, STATUS_ERROR, "Missing filename")
            return
        filename = parts[1]
        
        target_path = self.files.get_file_path(user, filename)
        if target_path is None:
            proto.send_message(CODE_FORBIDDEN, STATUS_ERROR, "Path traversal rejected")
            return
            
        size = self.files.get_file_size(user, filename)
        if size is None:
            proto.send_message(CODE_NOT_FOUND, STATUS_ERROR, "File not found")
            return

        proto.send_message(CODE_OK, STATUS_OK, str(size))
        addr = getattr(proto, "client_addr", None)
        if addr:
            engine.on_socket_state_changed(addr, "TRANSFERRING")
        try:
            sent = 0
            with open(target_path, "rb") as fh:
                while sent < size:
                    if getattr(engine, '_shutdown_event').is_set():
                        raise ConnectionAbortedError("Server shutting down")
                    chunk = fh.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    proto.send_bytes(chunk)
                    sent += len(chunk)
            engine.on_log_message(f"Sent file '{filename}' to {user}")
        except Exception as exc:
            logger.error("Download error: %s", exc)
        finally:
            if addr:
                engine.on_socket_state_changed(addr, "IDLE")
