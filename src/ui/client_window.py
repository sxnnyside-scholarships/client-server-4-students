"""
Client Window
─────────────
GUI for connecting to the server, browsing files,
uploading and downloading.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.config import ConfigManager
from src.localization.locale_manager import LocaleManager
from src.network.client_backend import ClientBackend
from src.ui.themes.theme_manager import ThemeManager
from src.ui.widgets.common import BrandingFooter, format_file_size


class ClientWindow(QMainWindow):
    """File-transfer client interface."""

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

        self.backend = ClientBackend()
        self._current_path = ""  # relative path inside user sandbox

        self.setMinimumSize(720, 500)
        self._build_ui()
        self._wire_signals()
        self._set_connected_state(False)
        self.retranslate()

        self.locale.locale_changed.connect(self.retranslate)

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(12, 12, 12, 8)

        # ── connection bar ───────────────────────────────────
        conn = QGridLayout()
        conn.setHorizontalSpacing(12)
        conn.setVerticalSpacing(2)
        conn.setContentsMargins(0, 0, 0, 0)

        self.host_label = QLabel()
        self.host_label.setObjectName("formLabel")
        self.host_input = QLineEdit()
        self.host_input.setText(
            self.config.get_nested("client", "default_host", default="localhost")
        )

        self.port_label = QLabel()
        self.port_label.setObjectName("formLabel")
        self.port_input = QLineEdit()
        self.port_input.setText(
            str(self.config.get_nested("client", "default_port", default=2121))
        )
        self.port_input.setMaximumWidth(72)

        self.user_label = QLabel()
        self.user_label.setObjectName("formLabel")
        self.user_input = QLineEdit()
        self.user_input.setText("student")

        self.pass_label = QLabel()
        self.pass_label.setObjectName("formLabel")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setText("student")

        self.connect_btn = QPushButton()
        self.connect_btn.setObjectName("primaryButton")
        self.disconnect_btn = QPushButton()

        self.back_btn = QPushButton()

        # Row 0: labels
        conn.addWidget(self.host_label, 0, 0)
        conn.addWidget(self.port_label, 0, 1)
        conn.addWidget(self.user_label, 0, 2)
        conn.addWidget(self.pass_label, 0, 3)
        # Row 1: inputs + action buttons
        conn.addWidget(self.host_input, 1, 0)
        conn.addWidget(self.port_input, 1, 1)
        conn.addWidget(self.user_input, 1, 2)
        conn.addWidget(self.pass_input, 1, 3)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.connect_btn)
        actions.addWidget(self.disconnect_btn)
        actions.addStretch()
        actions.addWidget(self.back_btn)
        conn.addLayout(actions, 1, 4)

        conn.setColumnStretch(0, 3)
        conn.setColumnStretch(1, 1)
        conn.setColumnStretch(2, 2)
        conn.setColumnStretch(3, 2)
        conn.setColumnStretch(4, 4)

        root.addLayout(conn)

        # ── toolbar ──────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.path_label = QLabel()
        self.path_label.setObjectName("pathLabel")

        self.go_up_btn = QPushButton()
        self.refresh_btn = QPushButton()
        self.new_folder_btn = QPushButton()
        self.upload_btn = QPushButton()
        self.upload_btn.setObjectName("primaryButton")
        self.download_btn = QPushButton()

        toolbar.addWidget(self.path_label, 1)
        toolbar.addWidget(self.go_up_btn)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.new_folder_btn)
        toolbar.addSpacing(8)
        toolbar.addWidget(self.upload_btn)
        toolbar.addWidget(self.download_btn)

        root.addLayout(toolbar)

        # ── file table ───────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self._on_row_double_clicked)

        root.addWidget(self.table)

        # ── progress bar ─────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        root.addWidget(self.progress)

        # ── branding footer ──────────────────────────────────
        self.footer = BrandingFooter()
        root.addWidget(self.footer)

        # ── status bar ───────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    # ── signals ───────────────────────────────────────────────

    def _wire_signals(self):
        self.connect_btn.clicked.connect(self._do_connect)
        self.disconnect_btn.clicked.connect(self._do_disconnect)
        self.back_btn.clicked.connect(self.close)
        self.refresh_btn.clicked.connect(self._refresh)
        self.go_up_btn.clicked.connect(self._go_up)
        self.new_folder_btn.clicked.connect(self._new_folder)
        self.upload_btn.clicked.connect(self._upload)
        self.download_btn.clicked.connect(self._download)

        self.backend.auth_success.connect(self._on_auth_ok)
        self.backend.auth_failed.connect(self._on_auth_fail)
        self.backend.disconnected.connect(self._on_disconnected)
        self.backend.file_list_received.connect(self._populate_table)
        self.backend.upload_complete.connect(self._on_upload_done)
        self.backend.download_complete.connect(self._on_download_done)
        self.backend.directory_created.connect(self._refresh)
        self.backend.error_occurred.connect(self._on_error)
        self.backend.status_message.connect(self._show_status)
        self.backend.transfer_progress.connect(self.progress.setValue)

    # ── i18n ──────────────────────────────────────────────────

    def retranslate(self):
        t = self.locale.get
        self.setWindowTitle(t("client_title"))
        self.host_label.setText(t("host"))
        self.port_label.setText(t("port"))
        self.user_label.setText(t("username"))
        self.pass_label.setText(t("password"))
        self.connect_btn.setText(t("connect"))
        self.disconnect_btn.setText(t("disconnect"))
        self.back_btn.setText(t("back_to_launcher"))
        self.go_up_btn.setText(t("go_up"))
        self.refresh_btn.setText(t("refresh"))
        self.new_folder_btn.setText(t("new_folder"))
        self.upload_btn.setText(t("upload"))
        self.download_btn.setText(t("download"))
        self.table.setHorizontalHeaderLabels(
            [t("name_col"), t("size_col"), t("type_col")]
        )
        self._update_path_label()

        self.footer.update_text(t("footer_prefix"), t("footer_link"))

    # ── connection ────────────────────────────────────────────

    def _do_connect(self):
        host = self.host_input.text().strip() or "localhost"
        try:
            port = int(self.port_input.text())
        except ValueError:
            port = 2121
        user = self.user_input.text().strip()
        pwd = self.pass_input.text()

        self.config.set_nested("client", "default_host", host)
        self.config.set_nested("client", "default_port", port)

        self._show_status(self.locale.get("connecting"))
        self.backend.connect_to_server(host, port, user, pwd)

    def _do_disconnect(self):
        self.backend.disconnect()

    def _on_auth_ok(self):
        self._set_connected_state(True)
        self._show_status(
            self.locale.get("authenticated", user=self.user_input.text())
        )
        self._current_path = ""
        self._refresh()

    def _on_auth_fail(self, reason: str):
        self._set_connected_state(False)
        self._show_status(self.locale.get("auth_failed"))

    def _on_disconnected(self):
        self._set_connected_state(False)
        self.table.setRowCount(0)

    def _set_connected_state(self, connected: bool):
        """Toggle UI elements depending on connection state."""
        self.connect_btn.setEnabled(not connected)
        self.host_input.setEnabled(not connected)
        self.port_input.setEnabled(not connected)
        self.user_input.setEnabled(not connected)
        self.pass_input.setEnabled(not connected)

        self.disconnect_btn.setEnabled(connected)
        self.refresh_btn.setEnabled(connected)
        self.go_up_btn.setEnabled(connected)
        self.new_folder_btn.setEnabled(connected)
        self.upload_btn.setEnabled(connected)
        self.download_btn.setEnabled(connected)

    # ── file browser ──────────────────────────────────────────

    def _refresh(self):
        self.backend.list_files(self._current_path)

    def _populate_table(self, entries: list):
        t = self.locale.get
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            name_item = QTableWidgetItem(entry["name"])
            size_text = (
                format_file_size(entry["size"])
                if entry["type"] == "file"
                else "—"
            )
            size_item = QTableWidgetItem(size_text)
            size_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            type_text = (
                t("folder_type") if entry["type"] == "dir" else t("file_type")
            )
            type_item = QTableWidgetItem(type_text)

            # Store metadata for double-click navigation
            name_item.setData(Qt.ItemDataRole.UserRole, entry["type"])

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, size_item)
            self.table.setItem(row, 2, type_item)

        self._update_path_label()
        self.progress.setValue(0)

    def _on_row_double_clicked(self, index):
        """Navigate into a directory on double-click."""
        row = index.row()
        name_item = self.table.item(row, 0)
        if name_item is None:
            return
        entry_type = name_item.data(Qt.ItemDataRole.UserRole)
        if entry_type == "dir":
            dirname = name_item.text()
            if self._current_path:
                self._current_path = f"{self._current_path}/{dirname}"
            else:
                self._current_path = dirname
            self._refresh()

    def _go_up(self):
        if "/" in self._current_path:
            self._current_path = self._current_path.rsplit("/", 1)[0]
        else:
            self._current_path = ""
        self._refresh()

    def _update_path_label(self):
        t = self.locale.get
        if self._current_path:
            self.path_label.setText(t("current_path", path=self._current_path))
        else:
            self.path_label.setText(t("root_path"))

    # ── file operations ───────────────────────────────────────

    def _upload(self):
        t = self.locale.get
        path, _ = QFileDialog.getOpenFileName(self, t("select_upload_file"))
        if not path:
            return
        filename = Path(path).name
        if self._current_path:
            remote = f"{self._current_path}/{filename}"
        else:
            remote = filename
        self.backend.upload_file(path, remote)

    def _download(self):
        t = self.locale.get
        row = self.table.currentRow()
        if row < 0:
            self._show_status(t("no_selection"))
            return
        name_item = self.table.item(row, 0)
        entry_type = name_item.data(Qt.ItemDataRole.UserRole)
        if entry_type != "file":
            return
        filename = name_item.text()

        save_path, _ = QFileDialog.getSaveFileName(
            self, t("select_download_location"), filename
        )
        if not save_path:
            return
        if self._current_path:
            remote = f"{self._current_path}/{filename}"
        else:
            remote = filename
        self.backend.download_file(remote, save_path)

    def _new_folder(self):
        t = self.locale.get
        name, ok = QInputDialog.getText(self, t("new_folder"), t("enter_folder_name"))
        if ok and name.strip():
            if self._current_path:
                full = f"{self._current_path}/{name.strip()}"
            else:
                full = name.strip()
            self.backend.create_directory(full)

    def _on_upload_done(self, filename: str):
        self._show_status(self.locale.get("upload_success", filename=filename))
        self._refresh()

    def _on_download_done(self, filename: str):
        self._show_status(self.locale.get("download_success", filename=filename))

    # ── feedback ──────────────────────────────────────────────

    def _on_error(self, msg: str):
        self._show_status(f"⚠ {msg}")

    def _show_status(self, msg: str):
        self.status_bar.showMessage(msg, 8000)

    # ── cleanup ───────────────────────────────────────────────

    def closeEvent(self, event):
        if self.backend.is_connected:
            self.backend.disconnect()
        self.closed.emit()
        event.accept()
