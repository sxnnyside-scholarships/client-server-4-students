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
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QProgressBar,
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
from src.network.transfer_state import TransferState
from src.ui.icons.icon_provider import get_icon
from src.ui.themes.theme_manager import ThemeManager
from src.ui.themes.tokens import icon_color
from src.ui.widgets.common import format_file_size
from src.ui.widgets.inspector import ProtocolInspectorWidget
from src.ui.widgets.nav_rail import NavRail
from src.ui.widgets.section_card import SectionCard
from src.ui.widgets.toggle_button import ToggleActionButton
from src.ui.widgets.atoms import MintButton, MintTextInput, EmptyStateWidget, Breadcrumb, MintIconButton, MintDialog

_ICON_SIZE = QSize(16, 16)


class TransferRow(QWidget):
    """
    A compact widget to display an active file transfer.

    Purpose:
    Renders direction icon, filename, and a slim progress bar for an active file transfer.

    Inputs:
    - filename: The name of the file being transferred.
    - is_upload: Boolean indicating if it's an upload (True) or download (False).
    - theme_name: The current theme.
    - locale: The LocaleManager instance.
    - cancel_callback: Optional callable to invoke when the cancel button is clicked.

    Outputs:
    - A QWidget representing the transfer progress.

    Side Effects:
    - May invoke `cancel_callback` when the cancel button is clicked.

    Failure Behavior:
    - If `cancel_callback` is not provided, the cancel button is simply omitted.

    ## Educational Note
    This widget is manipulated by the main thread in response to progress signals emitted by the
    background `ClientBackend` worker thread. This pattern ensures the GUI does not freeze during
    long network operations.
    """

    def __init__(
        self, filename: str, is_upload: bool, theme_name: str, locale: LocaleManager, cancel_callback=None, parent=None
    ):
        super().__init__(parent)
        self.filename = filename

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(get_icon("upload" if is_upload else "download", icon_color(theme_name)).pixmap(14, 14))
        layout.addWidget(self.icon_label)

        self.name_label = QLabel(filename)
        self.name_label.setObjectName("transferRowLabel")
        layout.addWidget(self.name_label)

        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        layout.addWidget(self.progress, 1)

        self.cancel_btn = None
        if cancel_callback:
            self.cancel_btn = MintIconButton("stop", theme_name)
            self.cancel_btn.setIconSize(QSize(12, 12))
            self.cancel_btn.setToolTip(locale.get("client.transfer_row_tooltip"))
            self.cancel_btn.clicked.connect(lambda: cancel_callback(self.filename))
            layout.addWidget(self.cancel_btn)

    def set_cancellable(self, cancellable: bool):
        """Disables the cancel affordance once cancellation is in flight or
        the transfer has reached a terminal state."""
        if self.cancel_btn is not None:
            self.cancel_btn.setEnabled(cancellable)


class ClientWindow(QMainWindow):
    """
    The primary View for the student Client application in the MVC architecture.

    Why this class exists:
    It provides a graphical interface for students to connect to a CS4S server, browse files,
    and inspect raw protocol traffic.

    What it owns:
    - Instantiation and layout of the MintPy Design System widgets.
    - Wiring user interactions (button clicks, keyboard shortcuts) to the backend engine.
    - Responding to locale changes for dynamic translation.

    What it deliberately does not own:
    - Network communication. All socket logic is deferred to `ClientBackend`.
    - Authentication logic or file IO.

    ## Educational Note
    This class demonstrates how to keep a GUI responsive. Network operations (like downloading a file)
    can take seconds or minutes. If we ran them on the main thread, the UI would freeze. Instead, this
    class emits requests to the `ClientBackend` (which runs on a separate worker thread), and listens
    for PyQt signals (like `connected`, `transfer_progress`) to update the screen safely.
    """

    closed = pyqtSignal()

    def __init__(
        self,
        config: ConfigManager,
        locale: LocaleManager,
        themes: ThemeManager,
        app: QApplication,
        backend: ClientBackend,
        runtime=None,
    ):
        super().__init__()
        self.config = config
        self.locale = locale
        self.themes = themes
        self.app = app
        self.runtime = runtime

        self.backend = backend
        self._current_path = ""  # relative path inside user sandbox
        self._transfer_rows: dict[str, TransferRow] = {}
        # Direction is recorded here at request time because the transfer
        # engine only reports filename + state, never direction.
        self._transfer_is_upload: dict[str, bool] = {}
        self._theme_name = self.config.get("theme", "mint_light")
        self._connection_state = ("offline", "client.badge_disconnected", {})

        self.setMinimumSize(1180, 720)
        self._build_ui()
        self._wire_signals()
        self._set_connected_state(False)
        self.retranslate()
        self.host_input.setFocus()

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
        self._build_menu()

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

    def _build_menu(self):
        """
        Builds the File/View/Help menu bar mirroring every rail and toolbar
        action, so each one has a keyboard-discoverable path with a mnemonic.

        All titles and action texts are applied in `retranslate()`; only the
        structure, shortcuts, and signal wiring live here. Shortcuts are
        declared on the `QAction`s (not as separate `QShortcut`s) so they show
        up next to the menu entries, which is how students discover them.
        """
        menubar = self.menuBar()
        self.file_menu = menubar.addMenu("")
        self.view_menu = menubar.addMenu("")
        self.help_menu = menubar.addMenu("")

        self.action_connect = self.file_menu.addAction("")
        self.action_connect.triggered.connect(self.connection_toggle_btn.click)

        self.file_menu.addSeparator()
        self.action_upload = self.file_menu.addAction("")
        self.action_upload.setShortcut(QKeySequence("Ctrl+U"))
        self.action_upload.triggered.connect(self._upload)
        self.action_download = self.file_menu.addAction("")
        self.action_download.setShortcut(QKeySequence("Ctrl+D"))
        self.action_download.triggered.connect(self._download)
        self.action_new_folder = self.file_menu.addAction("")
        self.action_new_folder.setShortcut(QKeySequence("Ctrl+N"))
        self.action_new_folder.triggered.connect(self._new_folder)

        self.file_menu.addSeparator()
        self.action_close = self.file_menu.addAction("")
        self.action_close.setShortcut(QKeySequence("Ctrl+W"))
        self.action_close.triggered.connect(self.close)

        self.action_refresh = self.view_menu.addAction("")
        self.action_refresh.setShortcut(QKeySequence("Ctrl+R"))
        self.action_refresh.triggered.connect(self._refresh)
        self.action_go_up = self.view_menu.addAction("")
        self.action_go_up.setShortcut(QKeySequence("Alt+Up"))
        self.action_go_up.triggered.connect(self._go_up)

        self.view_menu.addSeparator()
        self.action_files = self.view_menu.addAction("")
        self.action_files.triggered.connect(lambda: self.rail.set_mode("files"))
        self.action_lab = self.view_menu.addAction("")
        self.action_lab.triggered.connect(lambda: self.rail.set_mode("lab"))

        self.action_about = self.help_menu.addAction("")
        self.action_about.triggered.connect(self._show_about)

    def _show_about(self):
        t = self.locale.get
        MintDialog.message(
            self,
            self._theme_name,
            t("launcher.app_title"),
            f"{t('launcher.version_label')}\n\n{t('common.footer_prefix')}",
        )

    def _build_connection_form(self):
        rail = self.rail

        self.host_label = QLabel()
        self.host_label.setObjectName("formLabel")
        self.host_input = MintTextInput(self._theme_name)
        self.host_input.setText(self.config.get_nested("client", "default_host", default="localhost"))

        self.port_label = QLabel()
        self.port_label.setObjectName("formLabel")
        self.port_input = MintTextInput(self._theme_name)
        self.port_input.setText(str(self.config.get_nested("client", "default_port", default=2121)))

        self.user_label = QLabel()
        self.user_label.setObjectName("formLabel")
        self.user_input = MintTextInput(self._theme_name)
        self.user_input.setText(self.config.get_nested("client", "default_user", default=""))

        self.pass_label = QLabel()
        self.pass_label.setObjectName("formLabel")
        self.pass_input = MintTextInput(self._theme_name)
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setText(self.config.get_nested("client", "default_password", default=""))

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
        self.host_input.setAccessibleName(self.locale.get("a11y.host"))
        self.port_input.setAccessibleName(self.locale.get("a11y.port"))
        self.user_input.setAccessibleName(self.locale.get("a11y.username"))
        self.pass_input.setAccessibleName(self.locale.get("a11y.password"))

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
        self.rename_btn = MintIconButton("edit", self._theme_name)
        self.delete_btn = MintIconButton("trash", self._theme_name)

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
        toolbar.addWidget(self.rename_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.download_btn)
        toolbar.addWidget(self.upload_btn)

        root.addLayout(toolbar)

        # ── file table ───────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)

        self.empty_state = EmptyStateWidget(self.locale.get("client.empty_directory"), self._theme_name, "leaf")
        self.empty_state.setVisible(False)

        # ── empty state ──────────────────────────────────────
        self.empty_not_connected = EmptyStateWidget(
            self.locale.get("client.empty_not_connected"), self._theme_name, "grass"
        )
        self.empty_not_connected.setVisible(True)

        # Wrap table and empty state in a simple stack/container, not a SectionCard
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.table)
        table_layout.addWidget(self.empty_state)
        table_layout.addWidget(self.empty_not_connected)

        root.addWidget(table_container, 1)

        # ── transfers area ─────────────────────────────────────
        self.transfers_container = QWidget()
        self.transfers_layout = QVBoxLayout(self.transfers_container)
        self.transfers_layout.setContentsMargins(0, 0, 0, 0)
        self.transfers_layout.setSpacing(0)
        root.addWidget(self.transfers_container)

        return page

    def _build_lab_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)

        self.inspector_card = SectionCard(self._theme_name, accent="sage")
        self.inspector = ProtocolInspectorWidget(
            locale=self.locale, icon_color=icon_color(self._theme_name), theme_name=self._theme_name
        )
        self.inspector_card.content_layout.addWidget(self.inspector)
        root.addWidget(self.inspector_card)

        return page

    # ── signals ───────────────────────────────────────────────

    def _wire_signals(self):
        """
        Connects UI widgets to internal view-controller methods.

        Purpose:
            Establishes the internal event loop routing for user interactions.
        """
        self.connection_toggle_btn.toggled.connect(self._on_connection_toggled)

        # Supplementary shortcuts. The primary shortcuts (Ctrl+R/N/U/D, Alt+Up)
        # live on the menu-bar QActions where they are discoverable; these two
        # are conventional aliases that have no natural menu entry.
        QShortcut(QKeySequence("F5"), self).activated.connect(self._refresh)
        QShortcut(QKeySequence("Backspace"), self).activated.connect(self._go_up)

        self.refresh_btn.clicked.connect(self._refresh)
        self.go_up_btn.clicked.connect(self._go_up)
        self.new_folder_btn.clicked.connect(self._new_folder)
        self.rename_btn.clicked.connect(self._do_rename)
        self.delete_btn.clicked.connect(self._do_delete)
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
        self.backend.transfer_progress_detailed.connect(self._on_transfer_progress_detailed)
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
        """
        Updates all visible text elements in the window when the locale changes.

        Purpose:
            Allows dynamic language switching without requiring an application restart.
        """
        t = self.locale.get
        self.setWindowTitle(t("client.title"))
        self.host_label.setText(t("client.host"))
        self.port_label.setText(t("client.port"))
        self.user_label.setText(t("client.username"))
        self.pass_label.setText(t("client.password"))
        self.host_input.setAccessibleName(t("a11y.host"))
        self.port_input.setAccessibleName(t("a11y.port"))
        self.user_input.setAccessibleName(t("a11y.username"))
        self.pass_input.setAccessibleName(t("a11y.password"))
        self.connection_toggle_btn.setText(
            t("client.disconnect") if self.connection_toggle_btn.isChecked() else t("client.connect")
        )
        self.upload_btn.setText(t("client.upload"))
        self.download_btn.setText(t("client.download"))
        self.files_nav_btn.setText(t("client.nav_files"))
        self.lab_nav_btn.setText(t("client.lab_view_btn"))
        self.rail.set_nav_section_label(t("client.nav_section_label"))
        self.rail.back_btn.setText(t("common.back"))
        self.inspector_card.set_title(t("inspector.title"))
        self.table.setHorizontalHeaderLabels([t("client.name_col"), t("client.size_col"), t("client.type_col")])
        self._update_path_label()

        self.connection_toggle_btn.setToolTip(
            t("tooltip.disconnect") if self.connection_toggle_btn.isChecked() else t("tooltip.connect")
        )
        self.rail.back_btn.setToolTip(t("tooltip.back"))
        self.go_up_btn.setToolTip(t("tooltip.go_up"))
        self.refresh_btn.setToolTip(t("tooltip.refresh"))
        self.new_folder_btn.setToolTip(t("tooltip.new_folder"))
        self.rename_btn.setToolTip(t("tooltip.rename"))
        self.delete_btn.setToolTip(t("tooltip.delete"))
        self.upload_btn.setToolTip(t("tooltip.upload"))
        self.download_btn.setToolTip(t("tooltip.download"))
        self.lab_nav_btn.setToolTip(t("tooltip.lab_view_client"))

        # Menu bar
        self.file_menu.setTitle(t("menu.file"))
        self.view_menu.setTitle(t("menu.view"))
        self.help_menu.setTitle(t("menu.help"))
        self.action_connect.setText(
            t("client.disconnect") if self.connection_toggle_btn.isChecked() else t("client.connect")
        )
        self.action_upload.setText(t("client.upload"))
        self.action_download.setText(t("client.download"))
        self.action_new_folder.setText(t("client.new_folder"))
        self.action_close.setText(t("common.close"))
        self.action_refresh.setText(t("client.refresh"))
        self.action_go_up.setText(t("client.go_up"))
        self.action_files.setText(t("client.nav_files"))
        self.action_lab.setText(t("client.lab_view_btn"))
        self.action_about.setText(t("menu.about"))

        self.inspector.retranslate()
        self.empty_state.set_message(t("client.empty_directory"))
        self.empty_not_connected.set_message(t("client.empty_not_connected"))

        state, text_key, kwargs = self._connection_state
        self.status_badge.set_state(state, t(text_key, **kwargs))

        self.rail.footer.update_text(t("common.footer_prefix"))

    @property
    def status_badge(self):
        return self.rail.status_badge

    # ── connection ────────────────────────────────────────────

    def _on_connection_toggled(self, checked: bool):
        t = self.locale.get
        self.connection_toggle_btn.setText(t("client.disconnect") if checked else t("client.connect"))
        self.connection_toggle_btn.setToolTip(t("tooltip.disconnect") if checked else t("tooltip.connect"))
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
        self._show_status(t("client.connecting"))
        self._set_status_badge("connecting", "client.badge_connecting")
        self.backend.connect_to_server(host, port, user, pwd)

    def _do_disconnect(self):
        self.backend.disconnect()

    def _on_auth_ok(self):
        self._set_connected_state(True)
        t = self.locale.get
        self._show_status(t("client.authenticated", user=self.user_input.text()))
        self._set_status_badge("online", "client.badge_connected", host=self.host_input.text())
        self._current_path = ""
        self._refresh()
        self.rtt_timer.start(3000)
        self.backend.measure_rtt()

    def _on_auth_fail(self, reason: str):
        self._set_connected_state(False)
        self._show_status(self.locale.get("client.auth_failed"))
        self._set_status_badge("error", "client.badge_auth_failed")

    def _on_disconnected(self):
        self._set_connected_state(False)
        self.table.setRowCount(0)
        self.rtt_timer.stop()
        self._set_status_badge("offline", "client.badge_disconnected")

        # Transfers cannot survive the socket; retire their rows immediately.
        self._transfer_is_upload.clear()
        for filename in list(self._transfer_rows):
            self._remove_transfer_row(filename)

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
        self.connection_toggle_btn.setText(t("client.disconnect") if connected else t("client.connect"))

        self.host_input.setEnabled(not connected)
        self.port_input.setEnabled(not connected)
        self.user_input.setEnabled(not connected)
        self.pass_input.setEnabled(not connected)

        self.refresh_btn.setEnabled(connected)
        self.go_up_btn.setEnabled(connected)
        self.new_folder_btn.setEnabled(connected)
        self.upload_btn.setEnabled(connected)

        self.action_connect.setText(t("client.disconnect") if connected else t("client.connect"))
        self.action_upload.setEnabled(connected)
        self.action_new_folder.setEnabled(connected)
        self.action_refresh.setEnabled(connected)
        self.action_go_up.setEnabled(connected)

        if not connected:
            self.table.setVisible(False)
            self.empty_state.setVisible(False)
            self.empty_not_connected.setVisible(True)
        else:
            self.empty_not_connected.setVisible(False)
            # The table vs empty_state logic is handled by _populate_table.

        self._on_table_selection_changed()

    # ── file browser ──────────────────────────────────────────

    def _on_table_selection_changed(self):
        item = self._current_item() if self.backend.is_connected else None
        is_file = item is not None and item.data(Qt.ItemDataRole.UserRole) == "file"
        self.download_btn.setEnabled(is_file)
        self.action_download.setEnabled(is_file)
        self.rename_btn.setEnabled(item is not None)
        self.delete_btn.setEnabled(item is not None)

    def _current_item(self) -> QTableWidgetItem | None:
        """Returns the name-column item of the selected row, or None when
        nothing is selected — the single guard every row-action goes through."""
        row = self.table.currentRow()
        return self.table.item(row, 0) if row >= 0 else None

    def _refresh(self):
        """
        Triggers a directory refresh. F5 triggers this, mirroring the convention used by
        most file browsers and avoiding an extra click for the common
        "did anything change on the server?" check.
        """
        self.backend.list_files(self._current_path)

    _ACTIVE_TRANSFER_STATES = frozenset(
        (TransferState.QUEUED.value, TransferState.STARTING.value, TransferState.RUNNING.value)
    )
    _TERMINAL_TRANSFER_STATES = frozenset(
        (TransferState.COMPLETED.value, TransferState.CANCELLED.value, TransferState.FAILED.value)
    )

    def _on_transfer_state_changed(self, filename: str, state: str):
        """
        Creates, updates, or retires the per-transfer progress row that
        mirrors this transfer's lifecycle.

        ## Educational Note
        These state strings originate on the transfer worker thread; Qt's
        queued signal delivery is what makes it safe for this method to touch
        widgets — the slot always runs on the GUI thread.
        """
        if state in self._ACTIVE_TRANSFER_STATES:
            if filename not in self._transfer_rows:
                row = TransferRow(
                    filename,
                    self._transfer_is_upload.get(filename, True),
                    self._theme_name,
                    self.locale,
                    cancel_callback=self.backend.cancel_transfer,
                )
                self._transfer_rows[filename] = row
                self.transfers_layout.addWidget(row)
        elif state == TransferState.CANCELLING.value:
            row = self._transfer_rows.get(filename)
            if row is not None:
                row.set_cancellable(False)
        elif state in self._TERMINAL_TRANSFER_STATES:
            self._transfer_is_upload.pop(filename, None)
            row = self._transfer_rows.get(filename)
            if row is not None:
                row.set_cancellable(False)
                if state == TransferState.COMPLETED.value:
                    row.progress.setValue(100)
                QTimer.singleShot(1500, lambda f=filename: self._remove_transfer_row(f))

    def _remove_transfer_row(self, filename: str):
        row = self._transfer_rows.pop(filename, None)
        if row:
            self.transfers_layout.removeWidget(row)
            row.deleteLater()

    def _on_transfer_progress_detailed(self, progress: dict):
        filename = progress.get("filename")
        if filename in self._transfer_rows:
            self._transfer_rows[filename].progress.setValue(progress.get("percentage", 0))

    def _populate_table(self, entries: list):
        t = self.locale.get
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            name_item = QTableWidgetItem(entry["name"])

            # Use icon for type
            icon_name = "folder" if entry["type"] == "dir" else "document"
            name_item.setIcon(get_icon(icon_name, icon_color(self._theme_name, "muted")))

            size_text = format_file_size(entry["size"]) if entry["type"] == "file" else "—"
            size_item = QTableWidgetItem(size_text)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            type_text = t("client.folder_type") if entry["type"] == "dir" else t("client.file_type")
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
        path, _ = QFileDialog.getOpenFileName(self, t("client.select_upload_file"))
        if not path:
            return
        filename = Path(path).name
        remote = f"{self._current_path}/{filename}" if self._current_path else filename
        self._transfer_is_upload[remote] = True
        self.backend.upload_file(path, remote)

    def _download(self):
        t = self.locale.get
        name_item = self._current_item()
        if name_item is None:
            self._show_status(t("client.no_selection"))
            return
        if name_item.data(Qt.ItemDataRole.UserRole) != "file":
            return
        filename = name_item.text()

        save_path, _ = QFileDialog.getSaveFileName(self, t("client.select_download_location"), filename)
        if not save_path:
            return
        remote = f"{self._current_path}/{filename}" if self._current_path else filename
        self._transfer_is_upload[remote] = False
        self.backend.download_file(remote, save_path)

    def _new_folder(self):
        t = self.locale.get
        name, ok = MintDialog.get_text(self, self._theme_name, t("client.new_folder"), t("client.enter_folder_name"))
        if ok and name.strip():
            self.backend.create_directory(self._remote_path(name.strip()))

    def _on_upload_done(self, filename: str):
        self._show_status(self.locale.get("client.upload_success", filename=filename))
        self._refresh()

    def _on_download_done(self, filename: str):
        self._show_status(self.locale.get("client.download_success", filename=filename))

    def _remote_path(self, name: str) -> str:
        """Joins a file name onto the current sandbox-relative directory."""
        return f"{self._current_path}/{name}" if self._current_path else name

    def _show_context_menu(self, position):
        row = self.table.rowAt(position.y())
        if row < 0:
            return

        self.table.selectRow(row)

        menu = QMenu(self)
        t = self.locale.get
        color = icon_color(self._theme_name)

        rename_action = menu.addAction(get_icon("edit", color), t("client.rename_action"))
        move_action = menu.addAction(get_icon("move", color), t("client.move_action"))
        delete_action = menu.addAction(get_icon("trash", color), t("client.delete_action"))

        action = menu.exec(self.table.viewport().mapToGlobal(position))

        if action == rename_action:
            self._do_rename()
        elif action == move_action:
            self._do_move()
        elif action == delete_action:
            self._do_delete()

    def _do_rename(self):
        name_item = self._current_item()
        if name_item is None:
            return
        old_name = name_item.text()

        t = self.locale.get
        new_name, ok = MintDialog.get_text(
            self, self._theme_name, t("client.rename_action"), t("client.enter_new_name"), text=old_name
        )
        new_name = new_name.strip()
        if ok and new_name and new_name != old_name:
            self.backend.rename_file(self._remote_path(old_name), self._remote_path(new_name))

    def _do_move(self):
        name_item = self._current_item()
        if name_item is None:
            return
        filename = name_item.text()

        t = self.locale.get
        dest_dir, ok = MintDialog.get_text(self, self._theme_name, t("client.move_action"), t("client.enter_destination"))
        if ok and dest_dir.strip():
            self.backend.move_file(self._remote_path(filename), dest_dir.strip())

    def _do_delete(self):
        name_item = self._current_item()
        if name_item is None:
            return
        filename = name_item.text()

        t = self.locale.get
        ok = MintDialog.confirm(
            self,
            self._theme_name,
            t("client.confirm_delete_title"),
            t("client.confirm_delete_message", filename=filename),
            danger=True,
        )
        if ok:
            self.backend.delete_file(self._remote_path(filename))

    def _on_action_completed(self, cmd: str):
        self._refresh()

    # ── feedback ──────────────────────────────────────────────

    def _on_error(self, code: str, msg: str):
        self._show_status(self.locale.get("client.error_status", code=code, msg=msg))
        self._set_status_badge("error", "client.badge_error")

    def _on_recovering(self, attempt: int, max_attempts: int):
        self._show_status(self.locale.get("client.reconnecting_status", attempt=attempt, max_attempts=max_attempts))
        self._set_status_badge("connecting", "client.badge_connecting")

    def _show_status(self, msg: str):
        self.status_bar.showMessage(msg, 8000)

    # ── cleanup ───────────────────────────────────────────────

    def closeEvent(self, event):
        if self.backend.is_connected:
            self.backend.disconnect()
        self.closed.emit()
        event.accept()
