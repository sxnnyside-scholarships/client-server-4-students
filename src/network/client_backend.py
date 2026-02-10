"""
Client Backend
──────────────
Networking engine for the client side.

Every potentially blocking operation (connect, upload, download …)
runs in a background thread and communicates results back to the
GUI through Qt signals.
"""

import logging
import socket
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from src.core.protocol import (
    AUTH_FAIL,
    AUTH_OK,
    BUFFER_SIZE,
    CMD_AUTH,
    CMD_DOWNLOAD,
    CMD_LIST,
    CMD_MKDIR,
    CMD_QUIT,
    CMD_UPLOAD,
    DONE,
    ProtocolHandler,
    READY,
    STATUS_ERROR,
    STATUS_OK,
)

logger = logging.getLogger("client")


class ClientBackend(QObject):
    """Threaded TCP client with Qt signal integration."""

    # Signals → UI
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    auth_success = pyqtSignal()
    auth_failed = pyqtSignal(str)
    file_list_received = pyqtSignal(list)
    upload_complete = pyqtSignal(str)
    download_complete = pyqtSignal(str)
    directory_created = pyqtSignal()
    error_occurred = pyqtSignal(str)
    status_message = pyqtSignal(str)
    transfer_progress = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._socket: socket.socket | None = None
        self._proto: ProtocolHandler | None = None
        self._connected = False
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── helpers ───────────────────────────────────────────────

    def _bg(self, fn, *args):
        """Run *fn* in a daemon thread."""
        threading.Thread(target=fn, args=args, daemon=True).start()

    def _fail_disconnected(self):
        self._connected = False
        self.disconnected.emit()

    # ── connect / disconnect ──────────────────────────────────

    def connect_to_server(self, host: str, port: int, user: str, pwd: str):
        self._bg(self._do_connect, host, port, user, pwd)

    def _do_connect(self, host, port, user, pwd):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((host, port))
            self._socket = sock
            self._proto = ProtocolHandler(sock)
            self._connected = True
            self.connected.emit()
            self.status_message.emit(f"Connected to {host}:{port}")

            # Authenticate
            self._proto.send_message(CMD_AUTH, user, pwd)
            resp = self._proto.recv_message()

            if resp[0] == STATUS_OK and len(resp) > 1 and resp[1] == AUTH_OK:
                self._socket.settimeout(30.0)
                self.auth_success.emit()
                self.status_message.emit(f"Authenticated as {user}")
            else:
                reason = resp[1] if len(resp) > 1 else "Unknown error"
                self.auth_failed.emit(reason)
                self.disconnect()
        except (ConnectionRefusedError, ConnectionError, OSError) as exc:
            self.error_occurred.emit(f"Connection failed: {exc}")
            self._connected = False

    def disconnect(self):
        if not self._connected:
            return
        try:
            if self._proto:
                self._proto.send_message(CMD_QUIT)
        except (OSError, ConnectionError):
            pass
        finally:
            self._connected = False
            if self._socket:
                try:
                    self._socket.close()
                except OSError:
                    pass
            self._socket = None
            self._proto = None
            self.disconnected.emit()
            self.status_message.emit("Disconnected")

    # ── LIST ──────────────────────────────────────────────────

    def list_files(self, path: str = ""):
        self._bg(self._do_list, path)

    def _do_list(self, path):
        with self._lock:
            if not self._connected or not self._proto:
                self.error_occurred.emit("Not connected")
                return
            try:
                self._proto.send_message(CMD_LIST, path)
                resp = self._proto.recv_message()
                if resp[0] == STATUS_OK:
                    entries = []
                    raw = resp[1] if len(resp) > 1 else ""
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
                    self.file_list_received.emit(entries)
                else:
                    err = resp[1] if len(resp) > 1 else "Unknown"
                    self.error_occurred.emit(f"List failed: {err}")
            except (ConnectionError, OSError) as exc:
                self.error_occurred.emit(f"Connection error: {exc}")
                self._fail_disconnected()

    # ── UPLOAD ────────────────────────────────────────────────

    def upload_file(self, local_path: str, remote_name: str):
        self._bg(self._do_upload, local_path, remote_name)

    def _do_upload(self, local_path, remote_name):
        with self._lock:
            if not self._connected or not self._proto:
                self.error_occurred.emit("Not connected")
                return
            try:
                fp = Path(local_path)
                size = fp.stat().st_size
                self._proto.send_message(CMD_UPLOAD, remote_name, size)
                resp = self._proto.recv_message()
                if resp[0] != STATUS_OK:
                    self.error_occurred.emit(resp[1] if len(resp) > 1 else "Rejected")
                    return

                sent = 0
                with open(fp, "rb") as fh:
                    while sent < size:
                        chunk = fh.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        self._proto.send_bytes(chunk)
                        sent += len(chunk)
                        pct = int(sent / size * 100) if size else 100
                        self.transfer_progress.emit(pct)

                resp = self._proto.recv_message()
                if resp[0] == STATUS_OK:
                    self.upload_complete.emit(remote_name)
                    self.status_message.emit(f"Uploaded: {remote_name}")
                else:
                    self.error_occurred.emit(resp[1] if len(resp) > 1 else "Failed")
            except (ConnectionError, OSError) as exc:
                self.error_occurred.emit(f"Upload error: {exc}")
                self._fail_disconnected()

    # ── DOWNLOAD ──────────────────────────────────────────────

    def download_file(self, remote_name: str, local_path: str):
        self._bg(self._do_download, remote_name, local_path)

    def _do_download(self, remote_name, local_path):
        with self._lock:
            if not self._connected or not self._proto:
                self.error_occurred.emit("Not connected")
                return
            try:
                self._proto.send_message(CMD_DOWNLOAD, remote_name)
                resp = self._proto.recv_message()
                if resp[0] != STATUS_OK:
                    self.error_occurred.emit(resp[1] if len(resp) > 1 else "Failed")
                    return

                size = int(resp[1])
                save = Path(local_path)
                save.parent.mkdir(parents=True, exist_ok=True)

                received = 0
                with open(save, "wb") as fh:
                    while received < size:
                        want = min(BUFFER_SIZE, size - received)
                        chunk = self._proto.recv_exact(want)
                        fh.write(chunk)
                        received += len(chunk)
                        pct = int(received / size * 100) if size else 100
                        self.transfer_progress.emit(pct)

                self.download_complete.emit(remote_name)
                self.status_message.emit(f"Downloaded: {remote_name}")
            except (ConnectionError, OSError) as exc:
                self.error_occurred.emit(f"Download error: {exc}")
                self._fail_disconnected()

    # ── MKDIR ─────────────────────────────────────────────────

    def create_directory(self, dirname: str):
        self._bg(self._do_mkdir, dirname)

    def _do_mkdir(self, dirname):
        with self._lock:
            if not self._connected or not self._proto:
                self.error_occurred.emit("Not connected")
                return
            try:
                self._proto.send_message(CMD_MKDIR, dirname)
                resp = self._proto.recv_message()
                if resp[0] == STATUS_OK:
                    self.status_message.emit(f"Created folder: {dirname}")
                    self.directory_created.emit()
                else:
                    err = resp[1] if len(resp) > 1 else "Failed"
                    self.error_occurred.emit(f"Mkdir failed: {err}")
            except (ConnectionError, OSError) as exc:
                self.error_occurred.emit(f"Error: {exc}")
                self._fail_disconnected()
