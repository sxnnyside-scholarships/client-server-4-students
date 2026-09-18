"""
Module: python_code_tab.py
──────────────────────────
Purpose: Interactive Python Socket Code Generator tab for CS4S Lab View.

Architectural Role:
Generates pure standard-library Python code (`import socket`, `import ssl`) demonstrating
how students can implement each network command in their own scripts without external frameworks.
Dynamically binds the client's current connection configuration (host, port, username, TLS).

MintPy Adherence:
- Monospace styling following typography tokens.
- Mint atomic buttons (`MintButton`, `MintDropdown`).
- Zero emojis; 100% localized via `LocaleManager`.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.icons.icon_provider import get_icon
from src.ui.themes.tokens import RADIUS, get_monospace_font, icon_color, surface_colors
from src.ui.widgets.atoms import MintButton


class PythonCodeWidget(QWidget):
    """
    Pedagogical Python code generator showing equivalent standard socket code.
    """

    OPERATIONS = [
        ("op_connect", "python_code.op_connect"),
        ("op_auth", "python_code.op_auth"),
        ("op_list", "python_code.op_list"),
        ("op_upload", "python_code.op_upload"),
        ("op_download", "python_code.op_download"),
        ("op_fs", "python_code.op_fs"),
        ("op_ping", "python_code.op_ping"),
        ("op_tls", "python_code.op_tls"),
        ("op_full", "python_code.op_full"),
    ]

    def __init__(
        self,
        locale=None,
        theme_name: str = "mint_light",
        host: str = "127.0.0.1",
        port: int = 2121,
        username: str = "admin",
        tls_enabled: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.locale = locale
        self._theme_name = theme_name
        self.host = host
        self.port = port
        self.username = username
        self.tls_enabled = tls_enabled

        self._build_ui()
        self._wire_signals()
        self.retranslate()
        self._update_snippet()

    def _t(self, key: str, **kwargs) -> str:
        if self.locale is None:
            return key
        return self.locale.get(key, **kwargs)

    def set_connection_params(self, host: str, port: int, username: str = "admin", tls_enabled: bool = False):
        self.host = host
        self.port = port
        self.username = username
        self.tls_enabled = tls_enabled
        self._update_snippet()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Header row ──────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(10)

        self.op_label = QLabel()
        self.op_label.setStyleSheet("font-size: 12px; font-weight: 700;")
        header.addWidget(self.op_label)

        self.op_combo = QComboBox()
        self.op_combo.setFixedHeight(34)
        self.op_combo.setStyleSheet(
            f"QComboBox {{ padding: 4px 12px; border: 1px solid #DFE6E9; "
            f"border-radius: {RADIUS['sm']}px; font-size: 13px; font-weight: 600; min-width: 260px; }}"
        )
        for op_id, op_key in self.OPERATIONS:
            self.op_combo.addItem(self._t(op_key), op_id)
        header.addWidget(self.op_combo)

        header.addStretch()

        self.copy_btn = MintButton("", self._theme_name)
        self.copy_btn.setIcon(get_icon("document", icon_color(self._theme_name)))
        self.copy_btn.setIconSize(QSize(16, 16))
        header.addWidget(self.copy_btn)

        self.save_btn = MintButton("", self._theme_name)
        self.save_btn.setIcon(get_icon("download", icon_color(self._theme_name)))
        self.save_btn.setIconSize(QSize(16, 16))
        header.addWidget(self.save_btn)

        root.addLayout(header)

        # ── Code Display Area ───────────────────────────────────
        self.code_viewer = QTextEdit()
        self.code_viewer.setReadOnly(True)
        code_font = get_monospace_font(12)
        code_font.setStyleHint(QFont.StyleHint.Monospace)
        self.code_viewer.setFont(code_font)

        colors = surface_colors(self._theme_name)
        bg = "#1B1F2B" if "dark" in self._theme_name else "#232838"
        fg = "#E8ECEF"
        self.code_viewer.setStyleSheet(
            f"QTextEdit {{ background-color: {bg}; color: {fg}; "
            f"border-radius: {RADIUS['md']}px; padding: 12px; font-family: monospace; border: none; }}"
        )
        root.addWidget(self.code_viewer, 2)

        # ── Educational Concepts Explanation ────────────────────
        self.notes_box = QWidget()
        self.notes_box.setObjectName("notesBox")
        notes_layout = QVBoxLayout(self.notes_box)
        notes_layout.setContentsMargins(14, 12, 14, 12)
        notes_layout.setSpacing(6)

        self.notes_title = QLabel()
        self.notes_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #7C9473;")
        notes_layout.addWidget(self.notes_title)

        self.notes_body = QLabel()
        self.notes_body.setWordWrap(True)
        self.notes_body.setStyleSheet("font-size: 12px; color: #636E72;")
        notes_layout.addWidget(self.notes_body)

        colors = surface_colors(self._theme_name)
        self.notes_box.setStyleSheet(
            f"#notesBox {{ background-color: {colors['surface']}; border: 1px solid {colors['border']}; "
            f"border-radius: {RADIUS['md']}px; }}"
        )
        root.addWidget(self.notes_box, 1)

    def _wire_signals(self):
        self.op_combo.currentIndexChanged.connect(self._update_snippet)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        self.save_btn.clicked.connect(self._save_script)

    def _get_snippet(self, op_id: str) -> tuple[str, str]:
        h = self.host
        p = self.port
        u = self.username

        if op_id == "op_connect":
            code = f'''import socket

HOST = "{h}"
PORT = {p}

# 1. Create a streaming IPv4 TCP socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 2. Establish connection to CS4S server
client_socket.connect((HOST, PORT))
print(f"Connected to CS4S Server at {{HOST}}:{{PORT}}")

# 3. Send protocol greeting (delimited by newline)
client_socket.sendall(b"HELLO|CS4S/2.0\\n")

# 4. Receive server response banner (e.g. 220 HELLO|CS4S/2.0)
response = client_socket.recv(1024).decode("utf-8")
print(f"Server response: {{response.strip()}}")

client_socket.close()
'''
            notes = (
                "TCP is a byte-stream protocol. Applications must implement message framing "
                "(here using the '\\n' delimiter) so the receiver knows where one command ends and the next begins."
            )

        elif op_id == "op_auth":
            code = f'''import socket

HOST = "{h}"
PORT = {p}
USERNAME = "{u}"
PASSWORD = "your_password_here"

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

# Handshake first
s.sendall(b"HELLO|CS4S/2.0\\n")
s.recv(1024)

# Transmit AUTH command
auth_cmd = f"AUTH|{{USERNAME}}|{{PASSWORD}}\\n".encode("utf-8")
s.sendall(auth_cmd)

response = s.recv(1024).decode("utf-8").strip()
print(f"Auth Response: {{response}}")

if response.startswith("230"):
    print("Authentication successful! Session is now authenticated.")
else:
    print(f"Authentication failed: {{response}}")

s.close()
'''
            notes = (
                "Status codes follow standard conventions: 2xx represents success (230 AUTH_OK), "
                "4xx represents client errors (430 AUTH_FAIL / 401 UNAUTHORIZED)."
            )

        elif op_id == "op_list":
            code = f'''import socket

HOST = "{h}"
PORT = {p}

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
s.sendall(b"HELLO|CS4S/2.0\\n"); s.recv(1024)
s.sendall(b"AUTH|{u}|admin123\\n"); s.recv(1024)

# Request directory listing of root folder
s.sendall(b"LIST|\\n")

buffer = ""
while True:
    data = s.recv(1024).decode("utf-8")
    if not data:
        break
    buffer += data
    if "\\n" in buffer:
        break

print("Directory Listing Result:")
print(buffer.strip())
s.close()
'''
            notes = (
                "When reading stream sockets, network fragmentation can deliver data across multiple packets. "
                "Always buffer incoming data until complete delimiters are assembled."
            )

        elif op_id == "op_upload":
            code = f'''import socket
from pathlib import Path

HOST = "{h}"
PORT = {p}
FILE_PATH = Path("document.txt")

data_bytes = FILE_PATH.read_bytes()
file_size = len(data_bytes)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
s.sendall(b"HELLO|CS4S/2.0\\n"); s.recv(1024)
s.sendall(b"AUTH|{u}|admin123\\n"); s.recv(1024)

# 1. Send UPLOAD command header with file metadata
s.sendall(f"UPLOAD|{{FILE_PATH.name}}|{{file_size}}\\n".encode("utf-8"))
ack = s.recv(1024).decode("utf-8")

# 2. Stream binary payload in 4096-byte chunks
CHUNK_SIZE = 4096
for offset in range(0, file_size, CHUNK_SIZE):
    chunk = data_bytes[offset : offset + CHUNK_SIZE]
    s.sendall(chunk)

# 3. Read completion response (226 TRANSFER_DONE)
result = s.recv(1024).decode("utf-8")
print(f"Upload completed: {{result.strip()}}")
s.close()
'''
            notes = (
                "Chunked streaming allows transferring large files without loading them entirely into memory, "
                "preventing out-of-memory crashes on resource-constrained hosts."
            )

        elif op_id == "op_download":
            code = f'''import socket

HOST = "{h}"
PORT = {p}
REMOTE_FILENAME = "remote_document.txt"

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
s.sendall(b"HELLO|CS4S/2.0\\n"); s.recv(1024)
s.sendall(b"AUTH|{u}|admin123\\n"); s.recv(1024)

# Send DOWNLOAD request
s.sendall(f"DOWNLOAD|{{REMOTE_FILENAME}}\\n".encode("utf-8"))

# Read header containing file size (e.g. 200 READY|1024)
header = s.recv(1024).decode("utf-8")
print(f"Header: {{header.strip()}}")

file_bytes = bytearray()
while True:
    chunk = s.recv(4096)
    if not chunk:
        break
    file_bytes.extend(chunk)
    # Complete when expected size is reached or server sends 226
    if b"226 TRANSFER_DONE" in chunk:
        break

print(f"Downloaded {{len(file_bytes)}} bytes successfully!")
s.close()
'''
            notes = (
                "Protocol state transitions: The client requests a download, waits for server readiness header, "
                "swaps into binary stream consumption mode, and returns to command mode upon 226 code."
            )

        elif op_id == "op_fs":
            code = f'''import socket

HOST = "{h}"
PORT = {p}

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
s.sendall(b"HELLO|CS4S/2.0\\n"); s.recv(1024)
s.sendall(b"AUTH|{u}|admin123\\n"); s.recv(1024)

# Create folder
s.sendall(b"MKDIR|lab_reports\\n")
print("MKDIR:", s.recv(1024).decode("utf-8").strip())

# Rename file or folder
s.sendall(b"RENAME|lab_reports|final_reports\\n")
print("RENAME:", s.recv(1024).decode("utf-8").strip())

# Delete file or folder
s.sendall(b"DELETE|final_reports\\n")
print("DELETE:", s.recv(1024).decode("utf-8").strip())

s.close()
'''
            notes = (
                "Filesystem operations modify the server's sandboxed storage directory. "
                "The server validates all target paths to ensure directory traversal attacks are blocked."
            )

        elif op_id == "op_ping":
            code = f'''import socket
import time

HOST = "{h}"
PORT = {p}

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

# Measure Round-Trip Time (RTT)
t_start = time.perf_counter()
s.sendall(b"PING\\n")
response = s.recv(1024).decode("utf-8").strip()
t_end = time.perf_counter()

rtt_ms = (t_end - t_start) * 1000.0
print(f"Received: {{response}}")
print(f"Measured Round-Trip Time (RTT): {{rtt_ms:.2f}} ms")

s.close()
'''
            notes = (
                "Round-Trip Time (RTT) measures network transmission delay plus application processing latency. "
                "In high-latency networks, RTT directly determines throughput when using synchronous protocols."
            )

        elif op_id == "op_tls":
            code = f'''import socket
import ssl

HOST = "{h}"
PORT = {p}

# 1. Create TLS client SSLContext
context = ssl.create_default_context()
# For educational self-signed laboratory certificates:
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

# 2. Establish raw TCP connection
raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
raw_socket.connect((HOST, PORT))

# 3. Perform cryptographic TLS handshake over socket
secure_socket = context.wrap_socket(raw_socket, server_hostname=HOST)
print(f"TLS handshake established! Cipher: {{secure_socket.cipher()}}")

# 4. Transmit protocol commands through encrypted tunnel
secure_socket.sendall(b"HELLO|CS4S/2.0\\n")
print("Decrypted response:", secure_socket.recv(1024).decode("utf-8").strip())

secure_socket.close()
'''
            notes = (
                "Transport Layer Security (TLS) wraps the TCP byte stream in authenticated, encrypted record frames. "
                "Wireshark packet captures will show only Application Data rather than plaintext commands."
            )

        else:  # op_full
            code = f'''#!/usr/bin/env python3
"""
CS4S Standalone Client Script
Demonstrates a complete interactive socket lifecycle in pure Python.
"""
import socket
import sys

HOST = "{h}"
PORT = {p}

def run_client():
    print(f"Connecting to CS4S Server at {{HOST}}:{{PORT}}...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("Error: Could not connect to server. Is it running?")
        sys.exit(1)

    # 1. Handshake
    s.sendall(b"HELLO|CS4S/2.0\\n")
    banner = s.recv(1024).decode("utf-8").strip()
    print(f"Server Banner: {{banner}}")

    # 2. Authenticate
    username = input("Enter username [admin]: ").strip() or "{u}"
    password = input("Enter password [admin123]: ").strip() or "admin123"
    s.sendall(f"AUTH|{{username}}|{{password}}\\n".encode("utf-8"))
    auth_resp = s.recv(1024).decode("utf-8").strip()
    print(f"Auth: {{auth_resp}}")

    if not auth_resp.startswith("230"):
        print("Login failed. Exiting.")
        s.close()
        return

    # 3. Interactive loop
    print("\\nConnected! Type commands (LIST, PING, QUIT):")
    while True:
        try:
            cmd = input("cs4s> ").strip()
            if not cmd:
                continue
            if cmd.upper() == "QUIT":
                s.sendall(b"QUIT\\n")
                break
            s.sendall(f"{{cmd}}\\n".encode("utf-8"))
            resp = s.recv(4096).decode("utf-8").strip()
            print(resp)
        except (KeyboardInterrupt, EOFError):
            break

    s.close()
    print("Session closed gracefully.")

if __name__ == "__main__":
    run_client()
'''
            notes = (
                "This standalone script can be run directly from any terminal or operating system with Python 3 "
                "installed, without installing any third-party packages or GUI dependencies."
            )

        return code, notes

    def _update_snippet(self):
        idx = self.op_combo.currentIndex()
        if idx < 0:
            return
        op_id = self.op_combo.itemData(idx)
        code, notes = self._get_snippet(op_id)
        self.code_viewer.setPlainText(code)
        self.notes_body.setText(notes)

    def _copy_to_clipboard(self):
        code = self.code_viewer.toPlainText()
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(code)
        orig_text = self._t("python_code.copy_btn")
        self.copy_btn.setText(self._t("python_code.copied"))

        def _restore():
            try:
                self.copy_btn.setText(orig_text)
            except (RuntimeError, AttributeError):
                pass

        QTimer.singleShot(2000, _restore)

    def _save_script(self):
        default_name = "cs4s_client_snippet.py"
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._t("python_code.save_dialog_title"),
            default_name,
            "Python Files (*.py);;All Files (*)",
        )
        if path:
            try:
                Path(path).write_text(self.code_viewer.toPlainText(), encoding="utf-8")
                QMessageBox.information(
                    self,
                    self._t("python_code.save_dialog_title"),
                    self._t("python_code.save_success", path=path),
                )
            except Exception as exc:
                QMessageBox.warning(self, "Error", str(exc))

    def retranslate(self):
        self.op_label.setText(self._t("python_code.op_label"))
        self.copy_btn.setText(self._t("python_code.copy_btn"))
        self.save_btn.setText(self._t("python_code.save_btn"))
        self.notes_title.setText(self._t("python_code.notes_title"))

        current_idx = self.op_combo.currentIndex()
        self.op_combo.blockSignals(True)
        self.op_combo.clear()
        for op_id, op_key in self.OPERATIONS:
            self.op_combo.addItem(self._t(op_key), op_id)
        if current_idx >= 0:
            self.op_combo.setCurrentIndex(current_idx)
        self.op_combo.blockSignals(False)
        self._update_snippet()
