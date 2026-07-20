"""
Module: transfers.py
────────────────────
Purpose: Manages long-running upload and download byte-loops.

Architectural Role:
Isolates the slow, blocking operations of reading/writing large files over the 
network. By running these inside `engine.run_in_background` with chunked byte 
streams, it ensures the GUI remains responsive and can update progress bars dynamically.

Responsibilities:
- Stream bytes from disk to socket (`_do_upload`).
- Stream bytes from socket to disk (`_do_download`).
- Calculate transfer speeds and percentage completions in real-time.
- Handle active transfer cancellation gracefully without breaking the socket.

Expected Collaborators:
- `src.network.client.engine` (provides the socket lock and background thread executor).
- `src.network.client_backend` (consumes the progress callbacks).
"""

import threading
import time
from pathlib import Path
from typing import Callable

from src.core.protocol import (
    BUFFER_SIZE,
    CMD_DOWNLOAD,
    CMD_UPLOAD,
    CODE_ACTION_OK,
    CODE_OK,
)
from src.network.errors import NetworkError, map_socket_error
from src.network.transfer_state import TransferState

class ClientTransferEngine:
    """
    Manages background file transfers and cancellation logic.

    Why it exists:
    Sending a 1GB file cannot be done in a single blocking call. This engine breaks 
    files into `BUFFER_SIZE` chunks, allowing it to emit progress updates and check 
    for cancellation flags between chunks.

    Responsibilities:
    - Managing the read/write loops for file uploads and downloads.
    - Synchronizing cancellation events to pad byte streams safely.

    Non-Responsibilities (Anti-Goals):
    - It does NOT parse directory listings (delegated to Operations).
    - It does NOT reconnect a broken socket (delegated to Engine).
    """

    def __init__(self, engine):
        self.engine = engine
        
        # Callbacks
        self.on_transfer_state_changed: Callable[[str, str], None] = lambda x, y: None
        self.on_error_occurred: Callable[[str, str], None] = lambda x, y: None
        self.on_transfer_progress: Callable[[int], None] = lambda x: None
        self.on_transfer_progress_detailed: Callable[[dict], None] = lambda x: None
        self.on_upload_complete: Callable[[str], None] = lambda x: None
        self.on_download_complete: Callable[[str], None] = lambda x: None

    def cancel_transfer(self, remote_name: str):
        """
        Triggers the cancellation event for an active transfer.

        Args:
            remote_name: The string identifier of the file being transferred.

        Returns:
            None.

        Side Effects:
            Sets the `threading.Event` inside `engine.active_transfers`.

        Failure Behavior:
            If the transfer is not found, it fails silently (idempotent).
        """
        with self.engine.transfers_lock:
            if remote_name in self.engine.active_transfers:
                self.engine.active_transfers[remote_name].set()
                self.on_transfer_state_changed(remote_name, TransferState.CANCELLING.value)

    def upload_file(self, local_path: str, remote_name: str):
        """
        Asynchronously initiates a file upload.

        Args:
            local_path: The absolute path to the local file.
            remote_name: The destination relative path on the server.

        Returns:
            None.

        Side Effects:
            Spawns a background thread running `_do_upload`.

        Failure Behavior:
            None.
        """
        self.engine.run_in_background(self._do_upload, local_path, remote_name)

    def _do_upload(self, local_path, remote_name):
        cancel_event = threading.Event()
        with self.engine.transfers_lock:
            self.engine.active_transfers[remote_name] = cancel_event
        self.on_transfer_state_changed(remote_name, TransferState.QUEUED.value)

        with self.engine.lock:
            if not self.engine.is_connected or not self.engine.proto or self.engine.shutdown_event.is_set():
                self.engine.on_error_occurred(NetworkError.CONNECTION_LOST.value, "Not connected")
                self.on_transfer_state_changed(remote_name, TransferState.FAILED.value)
                with self.engine.transfers_lock:
                    self.engine.active_transfers.pop(remote_name, None)
                return
            try:
                self.on_transfer_state_changed(remote_name, TransferState.STARTING.value)
                fp = Path(local_path)
                size = fp.stat().st_size
                self.engine.proto.send_message(CMD_UPLOAD, remote_name, size)
                resp = self.engine.proto.recv_message()
                if resp[0] != str(CODE_OK):
                    self.engine.on_error_occurred(NetworkError.PROTOCOL_ERROR.value, resp[2] if len(resp) > 2 else "Rejected")
                    self.on_transfer_state_changed(remote_name, TransferState.FAILED.value)
                    return

                self.on_transfer_state_changed(remote_name, TransferState.RUNNING.value)
                sent = 0
                start_time = time.time()
                last_emit = 0.0

                with open(fp, "rb") as fh:
                    while sent < size:
                        if self.engine.shutdown_event.is_set():
                            raise ConnectionAbortedError("Client disconnected")
                            
                        if cancel_event.is_set():
                            want = min(BUFFER_SIZE, size - sent)
                            pad = b'\x00' * want
                            self.engine.proto.send_bytes(pad)
                            sent += len(pad)
                        else:
                            chunk = fh.read(BUFFER_SIZE)
                            if not chunk:
                                break
                            self.engine.proto.send_bytes(chunk)
                            sent += len(chunk)

                        now = time.time()
                        if now - last_emit > 0.1 or sent >= size:
                            pct = int(sent / size * 100) if size else 100
                            speed = (sent / (now - start_time)) if (now - start_time) > 0 else 0.0
                            self.on_transfer_progress(pct)
                            self.on_transfer_progress_detailed({
                                "filename": remote_name,
                                "bytes_transferred": sent,
                                "total_bytes": size,
                                "percentage": pct,
                                "speed_bps": speed
                            })
                            last_emit = now

                resp = self.engine.proto.recv_message()
                if cancel_event.is_set():
                    self.on_transfer_state_changed(remote_name, TransferState.CANCELLED.value)
                elif resp[0] == str(CODE_ACTION_OK):
                    self.on_upload_complete(remote_name)
                    self.engine.on_status_message(f"Uploaded: {remote_name}")
                    self.on_transfer_state_changed(remote_name, TransferState.COMPLETED.value)
                else:
                    self.engine.on_error_occurred(NetworkError.PROTOCOL_ERROR.value, resp[2] if len(resp) > 2 else "Failed")
                    self.on_transfer_state_changed(remote_name, TransferState.FAILED.value)
            except (ConnectionError, OSError) as exc:
                if self.engine.shutdown_event.is_set():
                    self.on_transfer_state_changed(remote_name, TransferState.CANCELLED.value)
                else:
                    self.engine.on_error_occurred(map_socket_error(exc).value, f"Upload error: {exc}")
                    self.on_transfer_state_changed(remote_name, TransferState.FAILED.value)
                    self.engine.fail_disconnected()
            finally:
                with self.engine.transfers_lock:
                    self.engine.active_transfers.pop(remote_name, None)

    def download_file(self, remote_name: str, local_path: str):
        """
        Asynchronously initiates a file download.

        Args:
            remote_name: The relative path of the remote file.
            local_path: The absolute path to save the file locally.

        Returns:
            None.

        Side Effects:
            Spawns a background thread running `_do_download`.

        Failure Behavior:
            None.
        """
        self.engine.run_in_background(self._do_download, remote_name, local_path)

    def _do_download(self, remote_name, local_path):
        cancel_event = threading.Event()
        with self.engine.transfers_lock:
            self.engine.active_transfers[remote_name] = cancel_event
        self.on_transfer_state_changed(remote_name, TransferState.QUEUED.value)

        with self.engine.lock:
            if not self.engine.is_connected or not self.engine.proto or self.engine.shutdown_event.is_set():
                self.engine.on_error_occurred(NetworkError.CONNECTION_LOST.value, "Not connected")
                self.on_transfer_state_changed(remote_name, TransferState.FAILED.value)
                with self.engine.transfers_lock:
                    self.engine.active_transfers.pop(remote_name, None)
                return
            try:
                self.on_transfer_state_changed(remote_name, TransferState.STARTING.value)
                self.engine.proto.send_message(CMD_DOWNLOAD, remote_name)
                resp = self.engine.proto.recv_message()
                if resp[0] != str(CODE_OK):
                    self.engine.on_error_occurred(NetworkError.PROTOCOL_ERROR.value, resp[2] if len(resp) > 2 else "Failed")
                    self.on_transfer_state_changed(remote_name, TransferState.FAILED.value)
                    return

                size = int(resp[2])
                save = Path(local_path)
                save.parent.mkdir(parents=True, exist_ok=True)

                self.on_transfer_state_changed(remote_name, TransferState.RUNNING.value)
                received = 0
                start_time = time.time()
                last_emit = 0.0

                with open(save, "wb") as fh:
                    while received < size:
                        if self.engine.shutdown_event.is_set():
                            raise ConnectionAbortedError("Client disconnected")
                            
                        want = min(BUFFER_SIZE, size - received)
                        chunk = self.engine.proto.recv_exact(want)
                        
                        if not cancel_event.is_set():
                            fh.write(chunk)
                        
                        received += len(chunk)

                        now = time.time()
                        if now - last_emit > 0.1 or received >= size:
                            pct = int(received / size * 100) if size else 100
                            speed = (received / (now - start_time)) if (now - start_time) > 0 else 0.0
                            self.on_transfer_progress(pct)
                            self.on_transfer_progress_detailed({
                                "filename": remote_name,
                                "bytes_transferred": received,
                                "total_bytes": size,
                                "percentage": pct,
                                "speed_bps": speed
                            })
                            last_emit = now

                if cancel_event.is_set():
                    try:
                        save.unlink(missing_ok=True)
                    except OSError:
                        pass
                    self.on_transfer_state_changed(remote_name, TransferState.CANCELLED.value)
                else:
                    self.on_download_complete(remote_name)
                    self.engine.on_status_message(f"Downloaded: {remote_name}")
                    self.on_transfer_state_changed(remote_name, TransferState.COMPLETED.value)
            except (ConnectionError, OSError) as exc:
                if self.engine.shutdown_event.is_set():
                    self.on_transfer_state_changed(remote_name, TransferState.CANCELLED.value)
                else:
                    self.engine.on_error_occurred(map_socket_error(exc).value, f"Download error: {exc}")
                    self.on_transfer_state_changed(remote_name, TransferState.FAILED.value)
                    self.engine.fail_disconnected()
            finally:
                with self.engine.transfers_lock:
                    self.engine.active_transfers.pop(remote_name, None)
