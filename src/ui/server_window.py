"""
Module: server_window.py
────────────────────────
Purpose: Provides the primary Graphical User Interface for the Server application.

Architectural Role:
Acts as a pure Facade/View component. It exposes the underlying `ServerBackend`
operations (start, stop, user management) through interactive Qt widgets.

Responsibilities:
- Render the Server UI as a `NavRail` (identity, bind form, status, mode switch) plus a
  `QStackedWidget` central area that switches between the Overview dashboard and Lab View —
  Lab View is a distinct full-size mode, not a panel squeezed beneath the dashboard.
- Observe `ServerBackend` signals to stream real-time logs and active connections.
- Allow teachers to add or remove student accounts dynamically via the `AuthManager`.
- Provide Lab View controls for latency and packet loss simulation.

Expected Collaborators:
- `src.network.server_backend.ServerBackend` (injected dependency)
- `src.storage.auth.AuthManager` (injected dependency)
- `src.ui.widgets.nav_rail.NavRail`
- `src.ui.widgets.section_card.SectionCard`
- `src.ui.widgets.graph.ConnectionGraphWidget`

Important Implementation Notes:
This file is strictly forbidden from executing direct socket operations or disk I/O.
All actions must delegate to the backend facades.
"""

from PyQt6.QtCore import QSize, QTimer, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QStackedWidget,
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
from src.ui.icons.icon_provider import get_icon
from src.ui.themes.theme_manager import ThemeManager
from datetime import datetime
from html import escape
from src.ui.themes.tokens import icon_color, status_color, surface_colors, text_color
from src.ui.widgets.graph import ConnectionGraphWidget
from src.ui.widgets.nav_rail import NavRail
from src.ui.widgets.section_card import SectionCard
from src.ui.widgets.toggle_button import ToggleActionButton
from src.ui.widgets.atoms import MintButton, MintTextInput, MintStepper, EmptyStateWidget, MintDialog, MintIconButton

_ICON_SIZE = QSize(16, 16)


class StatTile(QWidget):
    """
    A widget to display a single server statistic.

    Purpose:
    Renders a numeric or text value above a localized caption to show a server metric (e.g., TX/RX bytes).

    Inputs:
    - caption_key: The localization key for the tile's caption.
    - locale: The LocaleManager instance for translating the caption.
    - theme_name: The current UI theme name.
    - parent: The parent widget, if any.

    Outputs:
    - A QWidget displaying the statistic.

    Side Effects:
    - Translates its caption when `retranslate()` is called.

    Failure Behavior:
    - If the `caption_key` is missing, the raw key is displayed instead of a translation.
    """

    def __init__(self, caption_key: str, locale: LocaleManager, theme_name: str, parent=None):
        super().__init__(parent)
        self.caption_key = caption_key
        self.locale = locale

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.caption_label = QLabel(locale.get(caption_key))
        self.caption_label.setStyleSheet(f"font-size: 11px; color: {text_color(theme_name, 'muted')};")
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, value: str):
        self.value_label.setText(value)

    def retranslate(self):
        self.caption_label.setText(self.locale.get(self.caption_key))


class ServerWindow(QMainWindow):
    """
    The primary View for the educator Server application in the MVC architecture.

    Why this class exists:
    Provides educators with a dashboard to monitor active connections, manage authorized users,
    and manipulate network conditions (latency/packet loss) to demonstrate networking concepts.

    What it owns:
    - The dashboard layout and state representation of the Server backend.
    - Dispatching educator commands (like kicking a user or adding a password) to the backend.

    What it deliberately does not own:
    - It does not bind to ports, accept sockets, or route traffic.

    ## Educational Note
    Like the ClientWindow, this class operates on the Qt Main Thread. The actual server `select`
    event loop runs on a background daemon thread. By observing the separation between this class
    and the `ServerBackend`, students learn the standard producer-consumer pattern used in modern
    desktop applications.
    """

    closed = pyqtSignal()

    def __init__(
        self,
        config: ConfigManager,
        locale: LocaleManager,
        themes: ThemeManager,
        app: QApplication,
        auth: AuthManager,
        files: FileManager,
        backend: ServerBackend,
        runtime=None,
    ):
        super().__init__()
        self.config = config
        self.locale = locale
        self.themes = themes
        self.app = app
        self.runtime = runtime

        # Injected Core components
        self.auth = auth
        self.files = files
        self.backend = backend
        self._theme_name = self.config.get("theme", "mint_light")
        self.logger = setup_logger("server", self.runtime.logs_dir)

        self.setMinimumSize(1220, 760)
        self._build_ui()
        self._wire_signals()
        self.retranslate()
        self._refresh_user_list()
        self.new_user_input.setFocus()

        self.locale.locale_changed.connect(self.retranslate)

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setStyleSheet(f"QMainWindow {{ background-color: {surface_colors(self._theme_name)['background']}; }}")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── nav rail: identity, bind form, status, mode switch ────────
        self.rail = NavRail(self._theme_name)
        root.addWidget(self.rail)
        self._build_bind_form()

        self._build_menu()

        self.overview_nav_btn = self.rail.add_mode("overview", "terminal", "Overview", checked=True)
        self.users_nav_btn = self.rail.add_mode("users", "users", "Users")
        self.lab_nav_btn = self.rail.add_mode("lab", "flask", "Lab View")
        self.rail.mode_changed.connect(self._on_mode_changed)
        self.rail.back_requested.connect(self.close)

        # ── central content: Overview / Lab View, mutually exclusive ──
        content_wrap = QWidget()
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(20, 20, 20, 16)
        content_layout.setSpacing(12)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)
        root.addWidget(content_wrap, 1)

        self.overview_page = self._build_overview_page()
        self.stack.addWidget(self.overview_page)

        self.users_page = self._build_users_page()
        self.stack.addWidget(self.users_page)

        self.lab_page = self._build_lab_page()
        self.stack.addWidget(self.lab_page)

        # Status bar
        self.status_bar = QStatusBar()
        # Persistent "network impairment active" indicator: the latency/loss
        # steppers live in Lab View, but their effects apply everywhere — this
        # badge keeps the simulation visible from every page.
        self.impairment_badge = QLabel()
        self.impairment_badge.setStyleSheet(
            f"color: {status_color(self._theme_name, 'error')}; font-weight: 600; padding-right: 6px;"
        )
        self.impairment_badge.setVisible(False)
        self.status_bar.addPermanentWidget(self.impairment_badge)
        self.setStatusBar(self.status_bar)

    def _build_menu(self):
        """
        Builds the File/View/Help menu bar mirroring the rail actions, so
        each has a keyboard-discoverable path with a mnemonic.

        Titles and action texts are applied in `retranslate()`; only the
        structure, shortcuts, and signal wiring live here.
        """
        menubar = self.menuBar()
        self.file_menu = menubar.addMenu("")
        self.view_menu = menubar.addMenu("")
        self.help_menu = menubar.addMenu("")

        self.action_start = self.file_menu.addAction("")
        self.action_start.triggered.connect(self.server_toggle_btn.click)
        self.file_menu.addSeparator()
        self.action_close = self.file_menu.addAction("")
        self.action_close.setShortcut("Ctrl+W")
        self.action_close.triggered.connect(self.close)

        self.action_overview = self.view_menu.addAction("")
        self.action_overview.triggered.connect(lambda: self.rail.set_mode("overview"))
        self.action_users = self.view_menu.addAction("")
        self.action_users.triggered.connect(lambda: self.rail.set_mode("users"))
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

    def _build_bind_form(self):
        rail = self.rail

        self.host_label = QLabel()
        self.host_label.setObjectName("formLabel")
        self.host_input = MintTextInput(self._theme_name)
        self.host_input.setText(self.config.get_nested("server", "host", default="0.0.0.0"))

        self.port_label = QLabel()
        self.port_label.setObjectName("formLabel")
        self.port_input = MintTextInput(self._theme_name)
        self.port_input.setText(str(self.config.get_nested("server", "port", default=2121)))

        for label, field in (
            (self.host_label, self.host_input),
            (self.port_label, self.port_input),
        ):
            group = QVBoxLayout()
            group.setSpacing(4)
            group.addWidget(label)
            group.addWidget(field)
            rail.form_layout.addLayout(group)

        self.server_toggle_btn = ToggleActionButton(self._theme_name, "play", "stop")
        rail.form_layout.addWidget(self.server_toggle_btn)

        # Accessibility
        self.host_input.setAccessibleName(self.locale.get("a11y.bind_address"))
        self.port_input.setAccessibleName(self.locale.get("a11y.bind_port"))

        self.setTabOrder(self.host_input, self.port_input)
        self.setTabOrder(self.port_input, self.server_toggle_btn)

    def _build_overview_page(self) -> QWidget:
        page = QWidget()
        root = QGridLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # ── Left: Server Logs ────────────────────────────
        self.log_card = SectionCard(self._theme_name, accent="mint")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setObjectName("logArea")
        self.log_text.document().setMaximumBlockCount(2000)
        self.log_card.content_layout.addWidget(self.log_text)

        # Add log card header actions
        self.log_clear_btn = MintIconButton("eraser", self._theme_name)
        self.log_copy_btn = MintIconButton("document", self._theme_name)
        self.log_card.header_actions_layout.addWidget(self.log_copy_btn)
        self.log_card.header_actions_layout.addWidget(self.log_clear_btn)

        root.addWidget(self.log_card, 0, 0)

        # ── Right: Connected Clients ─────────────────────
        self.clients_card = SectionCard(self._theme_name, accent="mint")
        self.clients_list = QListWidget()
        self.clients_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.clients_list.customContextMenuRequested.connect(self._show_clients_context_menu)
        self.clients_empty = EmptyStateWidget(self.locale.get("server.empty_clients"), self._theme_name, "leaf")
        self.clients_empty.setVisible(True)
        self.clients_list.setVisible(False)
        self.clients_card.content_layout.addWidget(self.clients_list)
        self.clients_card.content_layout.addWidget(self.clients_empty)
        root.addWidget(self.clients_card, 0, 1)

        root.setColumnStretch(0, 3)
        root.setColumnStretch(1, 2)

        return page

    def _build_users_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)

        self.users_card = SectionCard(self._theme_name, accent="mint")
        self.users_list = QListWidget()
        self.users_list.itemSelectionChanged.connect(self._on_user_selection_changed)
        self.users_empty = EmptyStateWidget(self.locale.get("server.empty_users"), self._theme_name, "leaf")
        self.users_empty.setVisible(True)
        self.users_list.setVisible(False)
        self.users_card.content_layout.addWidget(self.users_list, 1)
        self.users_card.content_layout.addWidget(self.users_empty, 1)

        form = QHBoxLayout()
        form.setSpacing(12)
        form.setContentsMargins(0, 12, 0, 0)

        self.user_field_label = QLabel()
        self.user_field_label.setObjectName("formLabel")
        self.user_field_label.hide()  # We will use placeholders instead for compact layout
        self.new_user_input = MintTextInput(self._theme_name)
        self.new_user_input.setMinimumHeight(38)
        self.new_user_input.textChanged.connect(self._clear_user_error)

        self.pass_field_label = QLabel()
        self.pass_field_label.setObjectName("formLabel")
        self.pass_field_label.hide()
        self.new_pass_input = MintTextInput(self._theme_name)
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass_input.setMinimumHeight(38)
        self.new_pass_input.textChanged.connect(self._clear_user_error)

        form.addWidget(self.new_user_input, 1)
        form.addWidget(self.new_pass_input, 1)

        self.add_user_btn = MintButton("", self._theme_name)
        self.add_user_btn.setObjectName("primaryButton")
        self.add_user_btn.setIcon(get_icon("user-add", icon_color(self._theme_name, "on-accent")))
        self.add_user_btn.setIconSize(_ICON_SIZE)
        self.add_user_btn.setMinimumHeight(38)
        self.remove_user_btn = MintButton("", self._theme_name)
        self.remove_user_btn.setObjectName("dangerButton")
        self.remove_user_btn.setIcon(get_icon("user-x", icon_color(self._theme_name, "on-accent")))
        self.remove_user_btn.setIconSize(_ICON_SIZE)
        self.remove_user_btn.setMinimumHeight(38)

        form.addWidget(self.add_user_btn)
        form.addWidget(self.remove_user_btn)

        self.users_card.content_layout.addLayout(form)

        self.form_error_label = QLabel()
        self.form_error_label.setObjectName("formErrorLabel")
        self.form_error_label.setVisible(False)
        self.form_error_label.setStyleSheet(
            f"color: {status_color(self._theme_name, 'error')}; font-size: 13px; margin-top: 4px;"
        )
        self.users_card.content_layout.addWidget(self.form_error_label)

        root.addWidget(self.users_card)

        return page

    def _build_lab_page(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        self.controls_card = SectionCard(self._theme_name, accent="sage")
        self.latency_label = QLabel()
        self.controls_card.content_layout.addWidget(self.latency_label)
        self.latency_spin = MintStepper(self._theme_name)
        self.latency_spin.setRange(0.0, 5.0)
        self.latency_spin.setSingleStep(0.1)
        self.latency_spin.setSuffix(" s")
        self.controls_card.content_layout.addWidget(self.latency_spin)

        self.loss_label = QLabel()
        self.controls_card.content_layout.addWidget(self.loss_label)
        self.loss_spin = MintStepper(self._theme_name)
        self.loss_spin.setRange(0.0, 100.0)
        self.loss_spin.setSingleStep(1.0)
        self.loss_spin.setSuffix(" %")
        self.controls_card.content_layout.addWidget(self.loss_spin)
        self.controls_card.content_layout.addStretch()

        root.addWidget(self.controls_card, 1)

        self.graph = ConnectionGraphWidget(self._theme_name)
        root.addWidget(self.graph, 2)

        # Socket State Visualizer — a simplified per-connection state panel.
        # True kernel TCP states (ESTABLISHED/CLOSE_WAIT) aren't reliably
        # introspectable from Python userspace, so this tracks an
        # application-level approximation instead: IDLE (connected, no
        # active transfer) vs TRANSFERRING (an upload/download in flight).
        self.states_card = SectionCard(self._theme_name, accent="sage")
        self.socket_states_list = QListWidget()
        self.states_empty = EmptyStateWidget(self.locale.get("server.empty_sockets"), self._theme_name, "leaf")
        self.states_empty.setVisible(True)
        self.socket_states_list.setVisible(False)
        self.states_card.content_layout.addWidget(self.socket_states_list)
        self.states_card.content_layout.addWidget(self.states_empty)

        self._socket_states: dict[str, str] = {}

        self.stats_container = QWidget()
        self.stats_layout = QHBoxLayout(self.stats_container)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_layout.setSpacing(16)

        self.tile_tx = StatTile("server.stat_tx", self.locale, self._theme_name)
        self.tile_rx = StatTile("server.stat_rx", self.locale, self._theme_name)
        self.tile_conn = StatTile("server.stat_connections", self.locale, self._theme_name)
        self.tile_pkts = StatTile("server.stat_packets", self.locale, self._theme_name)

        self.stats_layout.addWidget(self.tile_tx)
        self.stats_layout.addWidget(self.tile_rx)
        self.stats_layout.addWidget(self.tile_conn)
        self.stats_layout.addWidget(self.tile_pkts)

        self.states_card.content_layout.addWidget(self.stats_container)

        root.addWidget(self.states_card, 1)
        return page

    # ── signals ───────────────────────────────────────────────

    def _wire_signals(self):
        """
        Connects UI widgets to internal view-controller methods.

        Purpose:
            Establishes the internal event loop routing for user interactions.
        """
        self.server_toggle_btn.toggled.connect(self._on_server_toggled)
        self.add_user_btn.clicked.connect(self._add_user)
        self.remove_user_btn.clicked.connect(self._remove_user)
        self.log_clear_btn.clicked.connect(self.log_text.clear)
        self.log_copy_btn.clicked.connect(self._copy_logs)

        self.backend.log_message.connect(self._append_log)
        self.backend.client_connected.connect(self._on_client_connected)
        self.backend.client_disconnected.connect(self._on_client_disconnected)
        self.backend.server_started.connect(self._on_started)
        self.backend.server_stopped.connect(self._on_stopped)

        # The backend exposes impairments as properties; the loss stepper shows
        # a percentage while the backend expects a 0.0–1.0 probability.
        self.latency_spin.valueChanged.connect(lambda v: setattr(self.backend, "simulate_latency", v))
        self.loss_spin.valueChanged.connect(lambda v: setattr(self.backend, "simulate_packet_loss", v / 100.0))
        self.latency_spin.valueChanged.connect(self._update_impairment_badge)
        self.loss_spin.valueChanged.connect(self._update_impairment_badge)

        self.backend.client_connected.connect(self.graph.add_client)
        self.backend.client_disconnected.connect(self.graph.remove_client)

        self.backend.client_connected.connect(self._on_socket_connected)
        self.backend.client_disconnected.connect(self._on_socket_disconnected)
        self.backend.socket_state_changed.connect(self._on_socket_state_changed)

        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(1000)
        self._last_stats = {"tx": 0, "rx": 0}

    def _on_mode_changed(self, mode: str):
        if mode == "users":
            self.stack.setCurrentWidget(self.users_page)
        elif mode == "lab":
            self.stack.setCurrentWidget(self.lab_page)
        else:
            self.stack.setCurrentWidget(self.overview_page)

    def _update_stats(self):
        """
        Refreshes the Lab View throughput readout once per second.

        Reports KB/s (computed as the byte delta since the last tick, since
        the poll interval is fixed at 1000ms) rather than cumulative raw byte
        counts, and includes the total packet (protocol message) count.
        """
        if self.backend.is_running:
            stats = self.backend.get_statistics()
            tx_rate = (stats["tx"] - self._last_stats["tx"]) / 1024.0
            rx_rate = (stats["rx"] - self._last_stats["rx"]) / 1024.0
            self._last_stats = stats

            self.tile_tx.set_value(f"{tx_rate:.1f}")
            self.tile_rx.set_value(f"{rx_rate:.1f}")
            self.tile_conn.set_value(str(stats["connections"]))
            self.tile_pkts.set_value(str(stats["packets"]))

    # ── i18n ──────────────────────────────────────────────────

    def retranslate(self):
        """
        Updates all visible text elements in the window when the locale changes.

        Purpose:
            Allows dynamic language switching without requiring an application restart.
        """
        t = self.locale.get
        self.setWindowTitle(t("server.title"))
        self.host_label.setText(t("server.bind_address"))
        self.port_label.setText(t("client.port"))
        self.host_input.setAccessibleName(t("a11y.bind_address"))
        self.port_input.setAccessibleName(t("a11y.bind_port"))
        self.server_toggle_btn.setText(
            t("server.stop_btn") if self.server_toggle_btn.isChecked() else t("server.start_btn")
        )
        self.log_text.setPlaceholderText(t("server.logs_placeholder"))
        self.log_card.set_title(t("server.logs"))
        self.clients_card.set_title(t("server.connections"))
        self.users_card.set_title(t("server.user_management"))
        self.add_user_btn.setText(t("server.add_user"))
        self.remove_user_btn.setText(t("server.remove_user"))
        self.user_field_label.setText(t("client.username"))
        self.pass_field_label.setText(t("client.password"))
        self.new_user_input.setPlaceholderText(t("server.username_placeholder"))
        self.new_pass_input.setPlaceholderText(t("server.password_placeholder"))
        self.overview_nav_btn.setText(t("client.nav_overview"))
        self.users_nav_btn.setText(t("server.users_list"))
        self.lab_nav_btn.setText(t("client.lab_view_btn"))
        self.rail.set_nav_section_label(t("client.nav_section_label"))
        self.rail.back_btn.setText(t("common.back"))
        self.controls_card.set_title(t("server.teacher_controls"))
        self.latency_label.setText(t("server.simulate_latency"))
        self.loss_label.setText(t("server.simulate_packet_loss"))
        self.states_card.set_title(t("server.socket_states"))

        self.clients_empty.set_message(t("server.empty_clients"))
        self.users_empty.set_message(t("server.empty_users"))
        self.states_empty.set_message(t("server.empty_sockets"))

        for tile in (self.tile_tx, self.tile_rx, self.tile_conn, self.tile_pkts):
            tile.retranslate()
            if not self.backend.is_running:
                tile.set_value("--")

        # Menu bar
        self.file_menu.setTitle(t("menu.file"))
        self.view_menu.setTitle(t("menu.view"))
        self.help_menu.setTitle(t("menu.help"))
        self.action_start.setText(
            t("server.stop_btn") if self.server_toggle_btn.isChecked() else t("server.start_btn")
        )
        self.action_close.setText(t("common.close"))
        self.action_overview.setText(t("client.nav_overview"))
        self.action_users.setText(t("server.users_list"))
        self.action_lab.setText(t("client.lab_view_btn"))
        self.action_about.setText(t("menu.about"))

        self.status_bar.showMessage(
            t("server.running", port=self.port_input.text()) if self.backend.is_running else t("server.stopped")
        )
        self.rail.status_badge.set_state(
            "online" if self.backend.is_running else "offline",
            t("server.badge_running", port=self.port_input.text())
            if self.backend.is_running
            else t("server.badge_stopped"),
        )

        self.server_toggle_btn.setToolTip(
            t("tooltip.stop_server") if self.server_toggle_btn.isChecked() else t("tooltip.start_server")
        )
        self.rail.back_btn.setToolTip(t("tooltip.back"))
        self.lab_nav_btn.setToolTip(t("tooltip.lab_view_server"))
        self.add_user_btn.setToolTip(t("tooltip.add_user"))
        self.remove_user_btn.setToolTip(t("tooltip.remove_user"))
        self.latency_spin.setToolTip(t("tooltip.simulate_latency"))
        self.loss_spin.setToolTip(t("tooltip.simulate_packet_loss"))
        self.log_clear_btn.setToolTip(t("tooltip.log_clear"))
        self.log_copy_btn.setToolTip(t("tooltip.log_copy"))
        self._render_socket_states()
        self._update_impairment_badge()

        self.rail.footer.update_text(t("common.footer_prefix"))

    # ── server lifecycle ──────────────────────────────────────

    def _on_server_toggled(self, checked: bool):
        t = self.locale.get
        self.server_toggle_btn.setText(t("server.stop_btn") if checked else t("server.start_btn"))
        self.server_toggle_btn.setToolTip(t("tooltip.stop_server") if checked else t("tooltip.start_server"))
        if checked:
            self._start_server()
        else:
            self._stop_server()

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
        self.server_toggle_btn.set_checked_silently(True)
        self.host_input.setEnabled(False)
        self.port_input.setEnabled(False)
        t = self.locale.get
        self.server_toggle_btn.setText(t("server.stop_btn"))
        self.action_start.setText(t("server.stop_btn"))
        self.status_bar.showMessage(t("server.running", port=self.port_input.text()))
        self.rail.status_badge.set_state("online", t("server.badge_running", port=self.port_input.text()))

    def _on_stopped(self):
        self.server_toggle_btn.set_checked_silently(False)
        self.host_input.setEnabled(True)
        self.port_input.setEnabled(True)
        self.clients_list.clear()
        self.clients_list.setVisible(False)
        self.clients_empty.setVisible(True)
        self._socket_states.clear()
        self._render_socket_states()
        t = self.locale.get
        self.server_toggle_btn.setText(t("server.start_btn"))
        self.action_start.setText(t("server.start_btn"))
        self.status_bar.showMessage(t("server.stopped"))
        self.rail.status_badge.set_state("offline", t("server.badge_stopped"))

    # ── log / client tracking ─────────────────────────────────

    def _copy_logs(self):
        QApplication.clipboard().setText(self.log_text.toPlainText())

    def _append_log(self, msg: str):
        """
        Appends one timestamped line to the log console.

        The message is HTML-escaped before insertion: log lines contain
        client-supplied data (usernames, filenames), which must never be
        interpreted as rich-text markup.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(
            f'<span style="color: {text_color(self._theme_name, "muted")};">[{timestamp}]</span> '
            f'<span style="color: {text_color(self._theme_name, "primary")};">{escape(msg)}</span>'
        )

    def _on_client_connected(self, addr: str):
        item = QListWidgetItem(addr)
        item.setIcon(get_icon("connect", icon_color(self._theme_name)))
        self.clients_list.addItem(item)
        self.clients_list.setVisible(True)
        self.clients_empty.setVisible(False)

    def _on_client_disconnected(self, addr: str):
        for i in range(self.clients_list.count()):
            if self.clients_list.item(i).text() == addr:
                self.clients_list.takeItem(i)
                break
        if self.clients_list.count() == 0:
            self.clients_list.setVisible(False)
            self.clients_empty.setVisible(True)

    def _on_socket_connected(self, addr: str):
        self._socket_states[addr] = "IDLE"
        self._render_socket_states()

    def _on_socket_disconnected(self, addr: str):
        self._socket_states.pop(addr, None)
        self._render_socket_states()

    def _on_socket_state_changed(self, addr: str, state: str):
        if addr in self._socket_states:
            self._socket_states[addr] = state
            self._render_socket_states()

    def _render_socket_states(self):
        t = self.locale.get
        state_labels = {
            "IDLE": t("server.socket_state_idle"),
            "TRANSFERRING": t("server.socket_state_transferring"),
        }
        self.socket_states_list.clear()
        for addr, state in self._socket_states.items():
            item = QListWidgetItem(f"{addr}  —  {state_labels.get(state, state)}")
            # "refresh" reads as neutral activity; a TRANSFERRING socket may be
            # streaming in either direction.
            item.setIcon(get_icon("terminal" if state == "IDLE" else "refresh", icon_color(self._theme_name)))
            self.socket_states_list.addItem(item)

        is_empty = len(self._socket_states) == 0
        self.socket_states_list.setVisible(not is_empty)
        self.states_empty.setVisible(is_empty)

    # ── user management ───────────────────────────────────────

    def _refresh_user_list(self):
        self.users_list.clear()
        users = self.auth.list_users()
        if not users:
            self.users_empty.setVisible(True)
            self.users_list.setVisible(False)
        else:
            self.users_empty.setVisible(False)
            self.users_list.setVisible(True)
            for user in users:
                item = QListWidgetItem(user)
                item.setIcon(get_icon("users", icon_color(self._theme_name)))
                self.users_list.addItem(item)
        self._on_user_selection_changed()

    def _show_user_error(self, msg: str):
        self.form_error_label.setText(msg)
        self.form_error_label.setVisible(True)

    def _clear_user_error(self, *args):
        self.form_error_label.setVisible(False)
        self.form_error_label.setText("")

    def _add_user(self):
        t = self.locale.get
        user = self.new_user_input.text().strip()
        pwd = self.new_pass_input.text()
        if not user:
            self._show_user_error(t("server.username_empty"))
            return
        if not pwd:
            self._show_user_error(t("server.password_empty"))
            return

        try:
            if self.auth.add_user(user, pwd):
                self._refresh_user_list()
                self.new_user_input.clear()
                self.new_pass_input.clear()
                self._clear_user_error()
                self._append_log(t("server.user_added", username=user))
            else:
                self._show_user_error(t("server.user_exists", username=user))
        except ValueError as e:
            self._show_user_error(str(e))

    def _remove_user(self):
        t = self.locale.get
        selected = self.users_list.selectedItems()
        if not selected:
            return

        username = selected[0].text()

        ok = MintDialog.confirm(
            self,
            self._theme_name,
            t("server.remove_user"),
            t("server.confirm_remove_user", username=username),
            danger=True,
        )
        if ok:
            self.auth.remove_user(username)
            self._refresh_user_list()
            self._append_log(t("server.user_removed", username=username))

    def _show_clients_context_menu(self, position):
        item = self.clients_list.itemAt(position)
        if not item:
            return

        self.clients_list.setCurrentItem(item)
        menu = QMenu()
        t = self.locale.get
        color = icon_color(self._theme_name)

        force_drop_action = menu.addAction(get_icon("disconnect", color), t("server.force_drop_client_btn"))
        action = menu.exec(self.clients_list.viewport().mapToGlobal(position))

        if action == force_drop_action:
            self._force_drop_client()

    def _force_drop_client(self):
        """
        Forcibly closes the selected client's socket after an explicit,
        target-naming confirmation — the drop is destructive and simulates a
        network failure, so the teacher must see exactly who is affected.
        """
        item = self.clients_list.currentItem()
        if item is None:
            return

        addr = item.text()
        t = self.locale.get
        ok = MintDialog.confirm(
            self,
            self._theme_name,
            t("server.force_drop_client_btn"),
            t("server.confirm_force_drop", addr=addr),
            danger=True,
        )
        if ok:
            self.backend.force_disconnect_client(addr)

    # ── impairment ─────────────────────────────────────────────────
    def _update_impairment_badge(self):
        latency = self.latency_spin.value()
        loss = self.loss_spin.value()

        if latency > 0 or loss > 0:
            t = self.locale.get
            self.impairment_badge.setText(t("server.impairment_active", latency=f"{latency:g}", loss=f"{loss:g}"))
            self.impairment_badge.setVisible(True)
        else:
            self.impairment_badge.setVisible(False)

    def _on_user_selection_changed(self):
        self.remove_user_btn.setEnabled(len(self.users_list.selectedItems()) > 0)

    # ── cleanup ───────────────────────────────────────────────

    def closeEvent(self, event):
        if self.backend.is_running:
            self.backend.stop()
        self.closed.emit()
        event.accept()
