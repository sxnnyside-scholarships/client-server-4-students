"""
Server Backend
──────────────
Networking engine for the server side.

Listens for incoming connections and spawns a thread per client.
Qt signals relay events to the GUI in a thread-safe way.
"""

import logging
import socket
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from src.core.protocol import (
    BUFFER_SIZE,
    CMD_AUTH,
    CMD_DOWNLOAD,
    CMD_LIST,
    CMD_MKDIR,
    CMD_QUIT,
    CMD_UPLOAD,
    DONE,
    GOODBYE,
    AUTH_FAIL,
    AUTH_OK,
    ProtocolHandler,
    READY,
    STATUS_ERROR,
    STATUS_OK,
)
from src.storage.auth import AuthManager
from src.storage.file_manager import FileManager

logger = logging.getLogger("server")


class ServerBackend(QObject):
    """Threaded TCP server with Qt signal integration."""

    # Signals → UI (always emitted from background threads;
    # Qt queues them automatically for the main thread)
    log_message = pyqtSignal(str)
    client_connected = pyqtSignal(str)
    client_disconnected = pyqtSignal(str)
    server_started = pyqtSignal()
    server_stopped = pyqtSignal()

    def __init__(self, auth: AuthManager, files: FileManager):
        super().__init__()
        self.auth = auth
        self.files = files
        self._socket: socket.socket | None = None
        self._running = False
        self._clients: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    # ── lifecycle ─────────────────────────────────────────────

    def start(self, host: str, port: int):
        """Bind, listen, and start accepting connections."""
        if self._running:
            return
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.settimeout(1.0)
            self._socket.bind((host, port))
            self._socket.listen(5)
            self._running = True

            threading.Thread(target=self._accept_loop, daemon=True).start()

            self.log_message.emit(f"Server started on {host}:{port}")
            logger.info("Server started on %s:%s", host, port)
            self.server_started.emit()
        except OSError as exc:
            self.log_message.emit(f"Failed to start server: {exc}")
            logger.error("Failed to start server: %s", exc)
            self._running = False

    def stop(self):
        """Shut down the server and drop every connected client."""
        if not self._running:
            return
        self._running = False

        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass

        with self._lock:
            self._clients.clear()

        self.log_message.emit("Server stopped")
        logger.info("Server stopped")
        self.server_stopped.emit()

    # ── connection handling ───────────────────────────────────

    def _accept_loop(self):
        """Accept new connections until the server is stopped."""
        while self._running:
            try:
                conn, addr = self._socket.accept()
                addr_str = f"{addr[0]}:{addr[1]}"

                t = threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr_str),
                    daemon=True,
                )
                with self._lock:
                    self._clients[addr_str] = t
                t.start()

                self.log_message.emit(f"Client connected: {addr_str}")
                logger.info("Client connected: %s", addr_str)
                self.client_connected.emit(addr_str)

            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_client(self, conn: socket.socket, addr: str):
        """Main loop for a single client thread."""
        proto = ProtocolHandler(conn)
        username: str | None = None

        try:
            while self._running:
                try:
                    parts = proto.recv_message()
                except ConnectionError:
                    break
                if not parts:
                    break

                cmd = parts[0].upper()

                if cmd == CMD_AUTH:
                    username = self._cmd_auth(proto, parts)

                elif cmd == CMD_LIST:
                    if not self._require_auth(proto, username):
                        continue
                    self._cmd_list(proto, parts, username)

                elif cmd == CMD_UPLOAD:
                    if not self._require_auth(proto, username):
                        continue
                    self._cmd_upload(proto, parts, username)

                elif cmd == CMD_DOWNLOAD:
                    if not self._require_auth(proto, username):
                        continue
                    self._cmd_download(proto, parts, username)

                elif cmd == CMD_MKDIR:
                    if not self._require_auth(proto, username):
                        continue
                    self._cmd_mkdir(proto, parts, username)

                elif cmd == CMD_QUIT:
                    proto.send_message(STATUS_OK, GOODBYE)
                    break

                else:
                    proto.send_message(STATUS_ERROR, "Unknown command")

        except Exception as exc:
            logger.error("Error handling %s: %s", addr, exc)
        finally:
            conn.close()
            with self._lock:
                self._clients.pop(addr, None)
            self.log_message.emit(f"Client disconnected: {addr}")
            logger.info("Client disconnected: %s", addr)
            self.client_disconnected.emit(addr)

    # ── guards ────────────────────────────────────────────────

    @staticmethod
    def _require_auth(proto: ProtocolHandler, username: str | None) -> bool:
        if username is None:
            proto.send_message(STATUS_ERROR, "Not authenticated")
            return False
        return True

    # ── command handlers ──────────────────────────────────────

    def _cmd_auth(self, proto: ProtocolHandler, parts: list) -> str | None:
        if len(parts) < 3:
            proto.send_message(STATUS_ERROR, AUTH_FAIL)
            return None
        user, pwd = parts[1], parts[2]
        if self.auth.verify(user, pwd):
            proto.send_message(STATUS_OK, AUTH_OK)
            self.log_message.emit(f"User '{user}' authenticated")
            logger.info("User '%s' authenticated", user)
            return user
        proto.send_message(STATUS_ERROR, AUTH_FAIL)
        self.log_message.emit(f"Auth failed for '{user}'")
        logger.warning("Auth failed for '%s'", user)
        return None

    def _cmd_list(self, proto: ProtocolHandler, parts: list, user: str):
        path = parts[1] if len(parts) > 1 else ""
        entries = self.files.list_directory(user, path)
        if entries is None:
            proto.send_message(STATUS_ERROR, "Invalid path")
            return
        encoded = ";".join(
            f"{e['name']}:{e['size']}:{e['type']}" for e in entries
        )
        proto.send_message(STATUS_OK, encoded)

    def _cmd_upload(self, proto: ProtocolHandler, parts: list, user: str):
        if len(parts) < 3:
            proto.send_message(STATUS_ERROR, "Missing filename or size")
            return
        filename = parts[1]
        try:
            size = int(parts[2])
        except ValueError:
            proto.send_message(STATUS_ERROR, "Invalid file size")
            return

        target = self.files.get_file_path(user, filename)
        if target is None:
            proto.send_message(STATUS_ERROR, "Invalid path")
            return

        target.parent.mkdir(parents=True, exist_ok=True)
        proto.send_message(STATUS_OK, READY)

        try:
            data = proto.recv_exact(size)
            with open(target, "wb") as fh:
                fh.write(data)
            proto.send_message(STATUS_OK, DONE)
            self.log_message.emit(f"'{user}' uploaded {filename} ({size} B)")
            logger.info("'%s' uploaded %s (%d bytes)", user, filename, size)
        except Exception as exc:
            proto.send_message(STATUS_ERROR, str(exc))
            logger.error("Upload error for '%s': %s", user, exc)

    def _cmd_download(self, proto: ProtocolHandler, parts: list, user: str):
        if len(parts) < 2:
            proto.send_message(STATUS_ERROR, "Missing filename")
            return
        filename = parts[1]
        target = self.files.get_file_path(user, filename)
        if target is None or not target.is_file():
            proto.send_message(STATUS_ERROR, "File not found")
            return

        size = target.stat().st_size
        proto.send_message(STATUS_OK, str(size))
        try:
            with open(target, "rb") as fh:
                while True:
                    chunk = fh.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    proto.send_bytes(chunk)
            self.log_message.emit(f"'{user}' downloaded {filename}")
            logger.info("'%s' downloaded %s (%d bytes)", user, filename, size)
        except Exception as exc:
            logger.error("Download error for '%s': %s", user, exc)

    def _cmd_mkdir(self, proto: ProtocolHandler, parts: list, user: str):
        if len(parts) < 2:
            proto.send_message(STATUS_ERROR, "Missing directory name")
            return
        dirname = parts[1]
        if self.files.create_directory(user, dirname):
            proto.send_message(STATUS_OK, "Directory created")
            self.log_message.emit(f"'{user}' created dir: {dirname}")
        else:
            proto.send_message(STATUS_ERROR, "Could not create directory")
