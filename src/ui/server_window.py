"""
Server Window
─────────────
GUI for running and managing the FTP-like server.
Provides controls for starting/stopping the server,
managing user accounts, and viewing real-time logs.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.config import ConfigManager
from src.core.logger import setup_logger
from src.localization.locale_manager import LocaleManager
from src.network.server_backend import ServerBackend
from src.storage.auth import AuthManager
from src.storage.file_manager import FileManager
from src.ui.themes.theme_manager import ThemeManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class ServerWindow(QMainWindow):
    """Server management interface."""

    closed = pyqtSignal()

    def __init__(
        self,
        config: ConfigManager,
        locale: LocaleManager,
        themes: ThemeManager,
        app: QApplication,
    ):
        super().__init__()
        self.config = config
        self.locale = locale
        self.themes = themes
        self.app = app

        # Core components
        self.auth = AuthManager(PROJECT_ROOT / "config" / "users.json")
        self.files = FileManager(PROJECT_ROOT / "server_files")
        self.backend = ServerBackend(self.auth, self.files)
        self.logger = setup_logger("server", PROJECT_ROOT / "logs")

        self.setMinimumSize(780, 520)
        self._build_ui()
        self._wire_signals()
        self.retranslate()
        self._refresh_user_list()

        self.locale.locale_changed.connect(self.retranslate)

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(12, 12, 12, 8)

        # ── top bar ──────────────────────────────────────────
        top = QHBoxLayout()

        self.host_label = QLabel()
        self.host_input = QLineEdit()
        self.host_input.setText(
            self.config.get_nested("server", "host", default="0.0.0.0")
        )
        self.host_input.setMaximumWidth(130)

        self.port_label = QLabel()
        self.port_input = QLineEdit()
        self.port_input.setText(
            str(self.config.get_nested("server", "port", default=2121))
        )
        self.port_input.setMaximumWidth(80)

        self.start_btn = QPushButton()
        self.start_btn.setObjectName("primaryButton")
        self.stop_btn = QPushButton()
        self.stop_btn.setEnabled(False)

        self.back_btn = QPushButton()

        top.addWidget(self.host_label)
        top.addWidget(self.host_input)
        top.addWidget(self.port_label)
        top.addWidget(self.port_input)
        top.addSpacing(8)
        top.addWidget(self.start_btn)
        top.addWidget(self.stop_btn)
        top.addStretch()
        top.addWidget(self.back_btn)

        root.addLayout(top)

        # ── main splitter ────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left — logs
        self.log_group = QGroupBox()
        log_lay = QVBoxLayout(self.log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setObjectName("logArea")
        log_lay.addWidget(self.log_text)

        # Right — clients + users
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)

        # Connected clients
        self.clients_group = QGroupBox()
        cl_lay = QVBoxLayout(self.clients_group)
        self.clients_list = QListWidget()
        cl_lay.addWidget(self.clients_list)

        # User management
        self.users_group = QGroupBox()
        ul_lay = QVBoxLayout(self.users_group)
        ul_lay.setSpacing(8)
        self.users_list = QListWidget()
        ul_lay.addWidget(self.users_list, 1)

        form = QGridLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 4, 0, 0)

        self.user_field_label = QLabel()
        self.user_field_label.setObjectName("formLabel")
        self.new_user_input = QLineEdit()
        self.new_user_input.setPlaceholderText("username")

        self.pass_field_label = QLabel()
        self.pass_field_label.setObjectName("formLabel")
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setPlaceholderText("password")
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        form.addWidget(self.user_field_label, 0, 0)
        form.addWidget(self.new_user_input, 0, 1)
        form.addWidget(self.pass_field_label, 1, 0)
        form.addWidget(self.new_pass_input, 1, 1)
        form.setColumnStretch(1, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.add_user_btn = QPushButton()
        self.add_user_btn.setObjectName("primaryButton")
        self.remove_user_btn = QPushButton()
        self.remove_user_btn.setObjectName("dangerButton")
        btn_row.addWidget(self.add_user_btn)
        btn_row.addWidget(self.remove_user_btn)
        btn_row.addStretch()
        form.addLayout(btn_row, 2, 0, 1, 2)

        ul_lay.addLayout(form)

        right_lay.addWidget(self.clients_group, 1)
        right_lay.addWidget(self.users_group, 2)

        splitter.addWidget(self.log_group)
        splitter.addWidget(right)
        splitter.setSizes([440, 320])

        root.addWidget(splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    # ── signals ───────────────────────────────────────────────

    def _wire_signals(self):
        self.start_btn.clicked.connect(self._start_server)
        self.stop_btn.clicked.connect(self._stop_server)
        self.back_btn.clicked.connect(self.close)
        self.add_user_btn.clicked.connect(self._add_user)
        self.remove_user_btn.clicked.connect(self._remove_user)

        self.backend.log_message.connect(self._append_log)
        self.backend.client_connected.connect(self._on_client_connected)
        self.backend.client_disconnected.connect(self._on_client_disconnected)
        self.backend.server_started.connect(self._on_started)
        self.backend.server_stopped.connect(self._on_stopped)

    # ── i18n ──────────────────────────────────────────────────

    def retranslate(self):
        t = self.locale.get
        self.setWindowTitle(t("server_title"))
        self.host_label.setText(t("bind_address"))
        self.port_label.setText(t("port"))
        self.start_btn.setText(t("start_server_btn"))
        self.stop_btn.setText(t("stop_server_btn"))
        self.back_btn.setText(t("back_to_launcher"))
        self.log_group.setTitle(t("logs"))
        self.clients_group.setTitle(t("connections"))
        self.users_group.setTitle(t("user_management"))
        self.add_user_btn.setText(t("add_user"))
        self.remove_user_btn.setText(t("remove_user"))
        self.user_field_label.setText(t("username"))
        self.pass_field_label.setText(t("password"))
        self.status_bar.showMessage(
            t("server_running", port=self.port_input.text())
            if self.backend.is_running
            else t("server_stopped")
        )

    # ── server lifecycle ──────────────────────────────────────

    def _start_server(self):
        host = self.host_input.text().strip() or "0.0.0.0"
        try:
            port = int(self.port_input.text())
        except ValueError:
            port = 2121

        self.config.set_nested("server", "host", host)
        self.config.set_nested("server", "port", port)
        self.backend.start(host, port)

    def _stop_server(self):
        self.backend.stop()

    def _on_started(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.host_input.setEnabled(False)
        self.port_input.setEnabled(False)
        t = self.locale.get
        self.status_bar.showMessage(
            t("server_running", port=self.port_input.text())
        )

    def _on_stopped(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.host_input.setEnabled(True)
        self.port_input.setEnabled(True)
        self.clients_list.clear()
        self.status_bar.showMessage(self.locale.get("server_stopped"))

    # ── log / client tracking ─────────────────────────────────

    def _append_log(self, msg: str):
        self.log_text.append(msg)

    def _on_client_connected(self, addr: str):
        self.clients_list.addItem(addr)

    def _on_client_disconnected(self, addr: str):
        for i in range(self.clients_list.count()):
            if self.clients_list.item(i).text() == addr:
                self.clients_list.takeItem(i)
                break

    # ── user management ───────────────────────────────────────

    def _refresh_user_list(self):
        self.users_list.clear()
        for name in self.auth.list_users():
            self.users_list.addItem(name)

    def _add_user(self):
        t = self.locale.get
        user = self.new_user_input.text().strip()
        pwd = self.new_pass_input.text()
        if not user:
            self.status_bar.showMessage(t("username_empty"))
            return
        if not pwd:
            self.status_bar.showMessage(t("password_empty"))
            return

        if self.auth.add_user(user, pwd):
            self._refresh_user_list()
            self._append_log(t("user_added", username=user))
            self.new_user_input.clear()
            self.new_pass_input.clear()
        else:
            self.status_bar.showMessage(t("user_exists", username=user))

    def _remove_user(self):
        t = self.locale.get
        item = self.users_list.currentItem()
        if item is None:
            return
        user = item.text()

        reply = QMessageBox.question(
            self,
            t("confirm"),
            t("confirm_remove_user", username=user),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.auth.remove_user(user)
            self._refresh_user_list()
            self._append_log(t("user_removed", username=user))

    # ── cleanup ───────────────────────────────────────────────

    def closeEvent(self, event):
        if self.backend.is_running:
            self.backend.stop()
        self.closed.emit()
        event.accept()
