"""
Module: client_window.py
────────────────────────
Purpose: Provides the primary Graphical User Interface for the Client application.

Architectural Role:
Acts as a pure Facade/View component. It translates user clicks into backend network requests
and translates backend Qt signals into visual updates (progress bars, file tables).

Responsibilities:
- Render the Client UI as a `NavRail` (identity, connection form, status, mode switch) plus a
  `QStackedWidget` central area that switches between the Files workflow and Lab View — Lab
  View is a distinct mode, not a panel squeezed alongside the file browser.
- Connect UI events (clicks, inputs) to `ClientBackend` methods.
- Observe `ClientBackend` signals to update the file table, status badge, and connection state.

Expected Collaborators:
- `src.network.client_backend.ClientBackend` (injected dependency)
- `src.ui.widgets.nav_rail.NavRail`
- `src.ui.widgets.section_card.SectionCard`
- `src.ui.widgets.inspector.ProtocolInspectorWidget`

Important Implementation Notes:
This file is strictly forbidden from executing direct socket I/O. All network operations
must be invoked by calling methods on the `ClientBackend`.
"""

from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.config import ConfigManager
from src.localization.locale_manager import LocaleManager
from src.network.client_backend import ClientBackend
from src.ui.icons.icon_provider import get_icon
from src.ui.themes.theme_manager import ThemeManager
from src.ui.themes.tokens import icon_color
from src.ui.widgets.common import format_file_size
from src.ui.widgets.inspector import ProtocolInspectorWidget
from src.ui.widgets.nav_rail import NavRail
from src.ui.widgets.section_card import SectionCard
from src.ui.widgets.toggle_button import ToggleActionButton
from src.ui.widgets.atoms import MintButton, MintTextInput, EmptyStateWidget, Breadcrumb, MintIconButton

_ICON_SIZE = QSize(16, 16)


class ClientWindow(QMainWindow):
    """
    Main file-transfer graphical client window.

    Why it exists:
    Provides the core interactive experience for students to test their server implementations
    without relying on command-line FTP clients. It acts as the visual harness for the network engine.

    Responsibilities:
    - Managing the visual state of the connection (enabling/disabling inputs).
    - Rendering the remote file directory in a `QTableWidget`.
    - Switching between the Files and Lab View content modes.

    Non-Responsibilities (Anti-Goals):
    - It does NOT parse network protocols.
    - It does NOT spawn background threads.
    """

    closed = pyqtSignal()

    def __init__(
        self,
        config: ConfigManager,
        locale: LocaleManager,
        themes: ThemeManager,
        app: QApplication,
        backend: ClientBackend,
        runtime = None,
    ):
        super().__init__()
        self.config = config
        self.locale = locale
        self.themes = themes
        self.app = app
        self.runtime = runtime

        self.backend = backend
        self._current_path = ""  # relative path inside user sandbox
        self._theme_name = self.config.get("theme", "mint_light")
        self._connection_state = ("offline", "badge_disconnected", {})

        self.setMinimumSize(1180, 720)
        self._build_ui()
        self._wire_signals()
        self._set_connected_state(False)
        self.retranslate()

        self.locale.locale_changed.connect(self.retranslate)

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── nav rail: identity, connection form, status, mode switch ──
        self.rail = NavRail(self._theme_name)
        root.addWidget(self.rail)
        self._build_connection_form()

        self.files_nav_btn = self.rail.add_mode("files", "folder", "Files", checked=True)
        self.lab_nav_btn = self.rail.add_mode("lab", "flask", "Lab View")
        self.rail.mode_changed.connect(self._on_mode_changed)
        self.rail.back_requested.connect(self.close)

        # ── central content: Files / Lab View, mutually exclusive ────
        content_wrap = QWidget()
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(20, 20, 20, 16)
        content_layout.setSpacing(12)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)
        root.addWidget(content_wrap, 1)

        self.files_page = self._build_files_page()
        self.stack.addWidget(self.files_page)

        self.lab_page = self._build_lab_page()
        self.stack.addWidget(self.lab_page)

        # ── status bar ───────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _build_connection_form(self):
        rail = self.rail

        self.host_label = QLabel()
        self.host_label.setObjectName("formLabel")
        self.host_input = MintTextInput(self._theme_name)
        self.host_input.setText(
            self.config.get_nested("client", "default_host", default="localhost")
        )

        self.port_label = QLabel()
        self.port_label.setObjectName("formLabel")
        self.port_input = MintTextInput(self._theme_name)
        self.port_input.setText(
            str(self.config.get_nested("client", "default_port", default=2121))
        )

        self.user_label = QLabel()
        self.user_label.setObjectName("formLabel")
        self.user_input = MintTextInput(self._theme_name)
        self.user_input.setText("student")

        self.pass_label = QLabel()
        self.pass_label.setObjectName("formLabel")
        self.pass_input = MintTextInput(self._theme_name)
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setText("student")

        for label, field in (
            (self.host_label, self.host_input),
            (self.port_label, self.port_input),
            (self.user_label, self.user_input),
            (self.pass_label, self.pass_input),
        ):
            group = QVBoxLayout()
            group.setSpacing(4)
            group.addWidget(label)
            group.addWidget(field)
            rail.form_layout.addLayout(group)

        # Connect/Disconnect used to be two side-by-side buttons that only
        # ever had one enabled at a time — the same "competing controls for
        # one binary state" pattern as Start/Stop Server. One toggle button.
        self.connection_toggle_btn = ToggleActionButton(self._theme_name, "connect", "disconnect")
        rail.form_layout.addWidget(self.connection_toggle_btn)

        # Accessibility
        self.host_input.setAccessibleName("Host address")
        self.port_input.setAccessibleName("Port number")
        self.user_input.setAccessibleName("Username")
        self.pass_input.setAccessibleName("Password")
        
        self.setTabOrder(self.host_input, self.port_input)
        self.setTabOrder(self.port_input, self.user_input)
        self.setTabOrder(self.user_input, self.pass_input)
        self.setTabOrder(self.pass_input, self.connection_toggle_btn)

    def _build_files_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # ── breadcrumb bar ───────────────────────────────────
        self.breadcrumb = Breadcrumb(self._theme_name)
        self.breadcrumb.path_clicked.connect(self._on_breadcrumb_clicked)
        root.addWidget(self.breadcrumb)

        # ── toolbar ──────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.setContentsMargins(4, 4, 4, 12)

        self.go_up_btn = MintIconButton("arrow-up", self._theme_name)
        self.refresh_btn = MintIconButton("refresh", self._theme_name)
        self.new_folder_btn = MintIconButton("folder-add", self._theme_name)
        
        self.upload_btn = MintButton("", self._theme_name)
        self.upload_btn.setObjectName("primaryButton")
        self.upload_btn.setIcon(get_icon("upload", icon_color(self._theme_name, "on-accent")))
        self.upload_btn.setIconSize(_ICON_SIZE)
        self.download_btn = MintButton("", self._theme_name)
        self.download_btn.setIcon(get_icon("download", icon_color(self._theme_name)))
        self.download_btn.setIconSize(_ICON_SIZE)

        toolbar.addWidget(self.go_up_btn)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.new_folder_btn)
        toolbar.addSpacing(8)
        toolbar.addStretch()
        toolbar.addWidget(self.upload_btn)
        toolbar.addWidget(self.download_btn)

        toolbar.addStretch()
        self.queue_label = QLabel()
        self.queue_label.setObjectName("queueLabel")
        self.queue_label.setVisible(False)
        toolbar.addWidget(self.queue_label)

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
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        self.empty_state = EmptyStateWidget("Directory is empty.", self._theme_name, "leaf")
        self.empty_state.setVisible(False)

        # Wrap table and empty state in a simple stack/container, not a SectionCard
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.table)
        table_layout.addWidget(self.empty_state)

        root.addWidget(table_container, 1)

        # ── progress bar ─────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        root.addWidget(self.progress)

        return page

    def _build_lab_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)

        self.inspector_card = SectionCard(self._theme_name, accent="sage")
        self.inspector = ProtocolInspectorWidget(
            locale=self.locale,
            icon_color=icon_color(self._theme_name),
            theme_name=self._theme_name
        )
        self.inspector_card.content_layout.addWidget(self.inspector)
        root.addWidget(self.inspector_card)

        return page

    # ── signals ───────────────────────────────────────────────

    def _wire_signals(self):
        self.connection_toggle_btn.toggled.connect(self._on_connection_toggled)
        self.refresh_btn.clicked.connect(self._refresh)
        self.go_up_btn.clicked.connect(self._go_up)
        self.new_folder_btn.clicked.connect(self._new_folder)
        self.upload_btn.clicked.connect(self._upload)
        self.download_btn.clicked.connect(self._download)
        self.inspector.raw_command_requested.connect(self.backend.send_raw)

        self.backend.auth_success.connect(self._on_auth_ok)
        self.backend.auth_failed.connect(self._on_auth_fail)
        self.backend.disconnected.connect(self._on_disconnected)
        self.backend.file_list_received.connect(self._populate_table)
        self.backend.upload_complete.connect(self._on_upload_done)
        self.backend.download_complete.connect(self._on_download_done)
        self.backend.directory_created.connect(self._refresh)
        self.backend.error_occurred.connect(self._on_error)
        self.backend.connection_recovering.connect(self._on_recovering)
        self.backend.status_message.connect(self._show_status)
        self.backend.transfer_progress.connect(self.progress.setValue)
        self.backend.transfer_state_changed.connect(self._on_transfer_state_changed)
        self.backend.action_completed.connect(self._on_action_completed)
        self.backend.packet_tx.connect(self.inspector.log_tx)
        self.backend.packet_rx.connect(self.inspector.log_rx)
        self.backend.rtt_measured.connect(self.inspector.set_rtt)

        self.rtt_timer = QTimer(self)
        self.rtt_timer.timeout.connect(self.backend.measure_rtt)

    def _on_mode_changed(self, mode: str):
        self.stack.setCurrentWidget(self.lab_page if mode == "lab" else self.files_page)

    # ── i18n ──────────────────────────────────────────────────

    def retranslate(self):
        t = self.locale.get
        self.setWindowTitle(t("client_title"))
        self.host_label.setText(t("host"))
        self.port_label.setText(t("port"))
        self.user_label.setText(t("username"))
        self.pass_label.setText(t("password"))
        self.connection_toggle_btn.setText(
            t("disconnect") if self.connection_toggle_btn.isChecked() else t("connect")
        )
        self.go_up_btn.setText(t("go_up"))
        self.refresh_btn.setText(t("refresh"))
        self.new_folder_btn.setText(t("new_folder"))
        self.upload_btn.setText(t("upload"))
        self.download_btn.setText(t("download"))
        self.files_nav_btn.setText(f"  {t('nav_files')}")
        self.lab_nav_btn.setText(f"  {t('lab_view_btn')}")
        self.rail.set_nav_section_label(t("nav_section_label"))
        self.rail.back_btn.setText(t("back_to_launcher"))
        self.inspector_card.set_title(t("protocol_inspector_title"))
        self.table.setHorizontalHeaderLabels(
            [t("name_col"), t("size_col"), t("type_col")]
        )
        self._update_path_label()

        self.connection_toggle_btn.setToolTip(
            t("tooltip_disconnect") if self.connection_toggle_btn.isChecked() else t("tooltip_connect")
        )
        self.rail.back_btn.setToolTip(t("tooltip_back"))
        self.go_up_btn.setToolTip(t("tooltip_go_up"))
        self.refresh_btn.setToolTip(t("tooltip_refresh"))
        self.new_folder_btn.setToolTip(t("tooltip_new_folder"))
        self.upload_btn.setToolTip(t("tooltip_upload"))
        self.download_btn.setToolTip(t("tooltip_download"))
        self.lab_nav_btn.setToolTip(t("tooltip_lab_view_client"))

        self.inspector.retranslate()
        self.empty_state.set_message(t("empty_directory"))

        state, text_key, kwargs = self._connection_state
        self.status_badge.set_state(state, t(text_key, **kwargs))

        self.rail.footer.update_text(t("footer_prefix"))

    @property
    def status_badge(self):
        return self.rail.status_badge

    # ── connection ────────────────────────────────────────────

    def _on_connection_toggled(self, checked: bool):
        t = self.locale.get
        self.connection_toggle_btn.setText(t("disconnect") if checked else t("connect"))
        self.connection_toggle_btn.setToolTip(
            t("tooltip_disconnect") if checked else t("tooltip_connect")
        )
        if checked:
            self._do_connect()
        else:
            self._do_disconnect()

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

        t = self.locale.get
        self._show_status(t("connecting"))
        self._set_status_badge("connecting", "badge_connecting")
        self.backend.connect_to_server(host, port, user, pwd)

    def _do_disconnect(self):
        self.backend.disconnect()

    def _on_auth_ok(self):
        self._set_connected_state(True)
        t = self.locale.get
        self._show_status(t("authenticated", user=self.user_input.text()))
        self._set_status_badge("online", "badge_connected", host=self.host_input.text())
        self._current_path = ""
        self._refresh()
        self.rtt_timer.start(3000)
        self.backend.measure_rtt()

    def _on_auth_fail(self, reason: str):
        self._set_connected_state(False)
        self._show_status(self.locale.get("auth_failed"))
        self._set_status_badge("error", "badge_auth_failed")

    def _on_disconnected(self):
        self._set_connected_state(False)
        self.table.setRowCount(0)
        self.rtt_timer.stop()
        self._set_status_badge("offline", "badge_disconnected")

    def _set_status_badge(self, state: str, text_key: str, **kwargs):
        """
        Updates the connection status badge and remembers the choice so
        `retranslate()` can re-apply the correct text after a language switch
        without needing to re-derive the current connection state.
        """
        self._connection_state = (state, text_key, kwargs)
        self.status_badge.set_state(state, self.locale.get(text_key, **kwargs))

    def _set_connected_state(self, connected: bool):
        """
        Toggles the enabled/disabled state of UI widgets based on connection status.

        Args:
            connected: True if the client is authenticated and ready, False otherwise.

        Returns:
            None.

        Side Effects:
            Mutates the `.enabled` property of multiple PyQt widgets and syncs
            the connection toggle button to the real backend state.

        Failure Behavior:
            None.
        """
        self.connection_toggle_btn.set_checked_silently(connected)
        t = self.locale.get
        self.connection_toggle_btn.setText(t("disconnect") if connected else t("connect"))

        self.host_input.setEnabled(not connected)
        self.port_input.setEnabled(not connected)
        self.user_input.setEnabled(not connected)
        self.pass_input.setEnabled(not connected)

        self.refresh_btn.setEnabled(connected)
        self.go_up_btn.setEnabled(connected)
        self.new_folder_btn.setEnabled(connected)
        self.upload_btn.setEnabled(connected)
        self.download_btn.setEnabled(connected)

    # ── file browser ──────────────────────────────────────────

    def keyPressEvent(self, event):
        """
        Handles window-level keyboard shortcuts.

        F5 triggers a directory refresh, mirroring the convention used by
        most file browsers and avoiding an extra click for the common
        "did anything change on the server?" check.
        """
        if event.key() == Qt.Key.Key_F5:
            self._refresh()
            return
        super().keyPressEvent(event)

    def _refresh(self):
        self.backend.list_files(self._current_path)

    def _on_transfer_state_changed(self, filename: str, state: str):
        active = len(self.backend.engine.active_transfers)
        if active > 0:
            self.queue_label.setText(self.locale.get("transfers_in_progress", count=active))
            self.queue_label.setVisible(True)
        else:
            self.queue_label.setVisible(False)

    def _populate_table(self, entries: list):
        t = self.locale.get
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            name_item = QTableWidgetItem(entry["name"])
            
            # Use icon for type
            icon_name = "folder" if entry["type"] == "dir" else "document"
            name_item.setIcon(get_icon(icon_name, icon_color(self._theme_name, "muted")))
            
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
            
        if len(entries) == 0:
            self.table.setVisible(False)
            self.empty_state.setVisible(True)
        else:
            self.table.setVisible(True)
            self.empty_state.setVisible(False)

        self._update_path_label()
        self.progress.setValue(0)

    def _on_row_double_clicked(self, index):
        """
        Navigates into a directory when a user double-clicks a table row.

        Args:
            index: The PyQt model index representing the clicked cell.

        Returns:
            None.

        Side Effects:
            Updates `self._current_path` and requests a new directory listing from the backend.

        Failure Behavior:
            Silently ignores double-clicks on files (only directories trigger navigation).
        """
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
        if self._current_path:
            self.breadcrumb.set_path(f"/{self._current_path}")
        else:
            self.breadcrumb.set_path("/")

    def _on_breadcrumb_clicked(self, path: str):
        if path == "/":
            self._current_path = ""
        else:
            self._current_path = path.lstrip("/")
        self._refresh()

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

    def _show_context_menu(self, position):
        row = self.table.rowAt(position.y())
        if row < 0:
            return

        self.table.selectRow(row)

        menu = QMenu()
        t = self.locale.get
        color = icon_color(self._theme_name)

        rename_action = menu.addAction(get_icon("edit", color), t("rename_action"))
        move_action = menu.addAction(get_icon("move", color), t("move_action"))
        delete_action = menu.addAction(get_icon("trash", color), t("delete_action"))

        action = menu.exec(self.table.viewport().mapToGlobal(position))

        if action == rename_action:
            self._do_rename(row)
        elif action == move_action:
            self._do_move(row)
        elif action == delete_action:
            self._do_delete(row)

    def _do_rename(self, row):
        name_item = self.table.item(row, 0)
        old_name = name_item.text()

        t = self.locale.get
        new_name, ok = QInputDialog.getText(
            self,
            t("rename_action"),
            t("enter_new_name"),
            text=old_name
        )
        if ok and new_name.strip() and new_name != old_name:
            if self._current_path:
                self.backend.rename_file(f"{self._current_path}/{old_name}", f"{self._current_path}/{new_name.strip()}")
            else:
                self.backend.rename_file(old_name, new_name.strip())

    def _do_move(self, row):
        name_item = self.table.item(row, 0)
        filename = name_item.text()

        t = self.locale.get
        dest_dir, ok = QInputDialog.getText(
            self,
            t("move_action"),
            t("enter_destination")
        )
        if ok and dest_dir.strip():
            if self._current_path:
                src_path = f"{self._current_path}/{filename}"
            else:
                src_path = filename
            self.backend.move_file(src_path, dest_dir.strip())

    def _do_delete(self, row):
        name_item = self.table.item(row, 0)
        filename = name_item.text()

        t = self.locale.get
        reply = QMessageBox.question(
            self,
            t("confirm_delete_title"),
            t("confirm_delete_message", filename=filename),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._current_path:
                self.backend.delete_file(f"{self._current_path}/{filename}")
            else:
                self.backend.delete_file(filename)

    def _on_action_completed(self, cmd: str):
        self._refresh()

    # ── feedback ──────────────────────────────────────────────

    def _on_error(self, code: str, msg: str):
        self._show_status(self.locale.get("error_status", code=code, msg=msg))
        self._set_status_badge("error", "badge_error")

    def _on_recovering(self, attempt: int, max_attempts: int):
        self._show_status(
            self.locale.get("reconnecting_status", attempt=attempt, max_attempts=max_attempts)
        )
        self._set_status_badge("connecting", "badge_connecting")

    def _show_status(self, msg: str):
        self.status_bar.showMessage(msg, 8000)

    # ── cleanup ───────────────────────────────────────────────

    def closeEvent(self, event):
        if self.backend.is_connected:
            self.backend.disconnect()
        self.closed.emit()
        event.accept()
