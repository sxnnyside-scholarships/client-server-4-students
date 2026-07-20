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

from PyQt6.QtCore import QSize, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
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
from src.ui.themes.tokens import icon_color
from src.ui.widgets.graph import ConnectionGraphWidget
from src.ui.widgets.nav_rail import NavRail
from src.ui.widgets.section_card import SectionCard
from src.ui.widgets.toggle_button import ToggleActionButton
from src.ui.widgets.atoms import MintButton, MintTextInput, MintStepper, EmptyStateWidget

_ICON_SIZE = QSize(16, 16)


class ServerWindow(QMainWindow):
    """
    Main server management console interface.

    Why it exists:
    Provides a visual control panel for instructors to run the server, monitor student
    connections in real time, and manage credentials without needing command-line skills.

    Responsibilities:
    - Toggling the server lifecycle through a single Start/Stop control.
    - Providing an interactive UI to modify `AuthManager` state.
    - Routing background engine logs into a read-only `QTextEdit`.
    - Switching between the Overview and Lab View content modes.

    Non-Responsibilities (Anti-Goals):
    - It does NOT listen on network ports.
    - It does NOT process file uploads.
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
        runtime = None,
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

        self.locale.locale_changed.connect(self.retranslate)

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── nav rail: identity, bind form, status, mode switch ────────
        self.rail = NavRail(self._theme_name)
        root.addWidget(self.rail)
        self._build_bind_form()

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
        self.setStatusBar(self.status_bar)

    def _build_bind_form(self):
        rail = self.rail

        self.host_label = QLabel()
        self.host_label.setObjectName("formLabel")
        self.host_input = MintTextInput(self._theme_name)
        self.host_input.setText(
            self.config.get_nested("server", "host", default="0.0.0.0")
        )

        self.port_label = QLabel()
        self.port_label.setObjectName("formLabel")
        self.port_input = MintTextInput(self._theme_name)
        self.port_input.setText(
            str(self.config.get_nested("server", "port", default=2121))
        )

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
        self.host_input.setAccessibleName("Bind address")
        self.port_input.setAccessibleName("Bind port")
        
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
        self.log_card.content_layout.addWidget(self.log_text)
        root.addWidget(self.log_card, 0, 0)

        # ── Right: Connected Clients ─────────────────────
        self.clients_card = SectionCard(self._theme_name, accent="mint")
        self.clients_list = QListWidget()
        self.clients_empty = EmptyStateWidget("No clients connected.", self._theme_name, "leaf")
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
        self.users_empty = EmptyStateWidget("No users configured.", self._theme_name, "user-x")
        self.users_empty.setVisible(True)
        self.users_list.setVisible(False)
        self.users_card.content_layout.addWidget(self.users_list, 1)
        self.users_card.content_layout.addWidget(self.users_empty, 1)

        form = QHBoxLayout()
        form.setSpacing(12)
        form.setContentsMargins(0, 12, 0, 0)

        self.user_field_label = QLabel()
        self.user_field_label.setObjectName("formLabel")
        self.user_field_label.hide() # We will use placeholders instead for compact layout
        self.new_user_input = MintTextInput(self._theme_name)
        self.new_user_input.setMinimumHeight(38)

        self.pass_field_label = QLabel()
        self.pass_field_label.setObjectName("formLabel")
        self.pass_field_label.hide()
        self.new_pass_input = MintTextInput(self._theme_name)
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass_input.setMinimumHeight(38)

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

        self.force_drop_btn = MintButton("", self._theme_name)
        self.force_drop_btn.setObjectName("dangerButton")
        self.force_drop_btn.setIcon(get_icon("disconnect", icon_color(self._theme_name, "on-accent")))
        self.force_drop_btn.setIconSize(_ICON_SIZE)
        self.controls_card.content_layout.addWidget(self.force_drop_btn)
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
        self.states_empty = EmptyStateWidget("No sockets active.", self._theme_name, "leaf")
        self.states_empty.setVisible(True)
        self.socket_states_list.setVisible(False)
        self.states_card.content_layout.addWidget(self.socket_states_list)
        self.states_card.content_layout.addWidget(self.states_empty)

        self._socket_states: dict[str, str] = {}

        self.stats_label = QLabel()
        self.stats_label.setObjectName("statsLabel")
        self.states_card.content_layout.addWidget(self.stats_label)

        root.addWidget(self.states_card, 1)
        return page

    # ── signals ───────────────────────────────────────────────

    def _wire_signals(self):
        self.server_toggle_btn.toggled.connect(self._on_server_toggled)
        self.add_user_btn.clicked.connect(self._add_user)
        self.remove_user_btn.clicked.connect(self._remove_user)

        self.backend.log_message.connect(self._append_log)
        self.backend.client_connected.connect(self._on_client_connected)
        self.backend.client_disconnected.connect(self._on_client_disconnected)
        self.backend.server_started.connect(self._on_started)
        self.backend.server_stopped.connect(self._on_stopped)

        self.latency_spin.valueChanged.connect(lambda v: setattr(self.backend, 'simulate_latency', v))
        self.loss_spin.valueChanged.connect(lambda v: setattr(self.backend, 'simulate_packet_loss', v / 100.0))
        self.force_drop_btn.clicked.connect(self._force_drop_client)

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
            tx_rate = (stats['tx'] - self._last_stats['tx']) / 1024.0
            rx_rate = (stats['rx'] - self._last_stats['rx']) / 1024.0
            self._last_stats = stats
            t = self.locale.get
            self.stats_label.setText(
                t(
                    "lab_stats_readout",
                    tx=f"{tx_rate:.1f}",
                    rx=f"{rx_rate:.1f}",
                    connections=stats['connections'],
                    packets=stats['packets'],
                )
            )

    # ── i18n ──────────────────────────────────────────────────

    def retranslate(self):
        t = self.locale.get
        self.setWindowTitle(t("server_title"))
        self.host_label.setText(t("bind_address"))
        self.port_label.setText(t("port"))
        self.server_toggle_btn.setText(
            t("stop_server_btn") if self.server_toggle_btn.isChecked() else t("start_server_btn")
        )
        self.log_text.setPlaceholderText(t("logs_placeholder"))
        self.clients_list.setToolTip(t("no_connections"))
        self.log_card.set_title(t("logs"))
        self.clients_card.set_title(t("connections"))
        self.users_card.set_title(t("user_management"))
        self.add_user_btn.setText(t("add_user"))
        self.remove_user_btn.setText(t("remove_user"))
        self.user_field_label.setText(t("username"))
        self.pass_field_label.setText(t("password"))
        self.new_user_input.setPlaceholderText(t("username_placeholder"))
        self.new_pass_input.setPlaceholderText(t("password_placeholder"))
        self.overview_nav_btn.setText(f"  {t('nav_overview')}")
        self.users_nav_btn.setText(f"  {t('nav_users', default='Users')}")
        self.lab_nav_btn.setText(f"  {t('lab_view_btn')}")
        self.rail.set_nav_section_label(t("nav_section_label"))
        self.rail.back_btn.setText(t("back_to_launcher"))
        self.controls_card.set_title(t("teacher_controls"))
        self.latency_label.setText(t("simulate_latency"))
        self.loss_label.setText(t("simulate_packet_loss"))
        self.force_drop_btn.setText(t("force_drop_client_btn"))
        self.states_card.set_title(t("socket_states"))
        
        self.clients_empty.set_message(t("empty_clients"))
        self.users_empty.set_message(t("empty_users"))
        self.states_empty.set_message(t("empty_sockets"))

        if not self.backend.is_running:
            self.stats_label.setText(t("lab_stats_idle"))
        self.status_bar.showMessage(
            t("server_running", port=self.port_input.text())
            if self.backend.is_running
            else t("server_stopped")
        )
        self.rail.status_badge.set_state(
            "online" if self.backend.is_running else "offline",
            t("badge_server_running", port=self.port_input.text())
            if self.backend.is_running
            else t("badge_server_stopped"),
        )

        self.server_toggle_btn.setToolTip(
            t("tooltip_stop_server") if self.server_toggle_btn.isChecked() else t("tooltip_start_server")
        )
        self.rail.back_btn.setToolTip(t("tooltip_back"))
        self.lab_nav_btn.setToolTip(t("tooltip_lab_view_server"))
        self.add_user_btn.setToolTip(t("tooltip_add_user"))
        self.remove_user_btn.setToolTip(t("tooltip_remove_user"))
        self.force_drop_btn.setToolTip(t("tooltip_force_drop"))
        self.latency_spin.setToolTip(t("tooltip_simulate_latency"))
        self.loss_spin.setToolTip(t("tooltip_simulate_packet_loss"))
        self._render_socket_states()

        self.rail.footer.update_text(t("footer_prefix"))

    # ── server lifecycle ──────────────────────────────────────

    def _on_server_toggled(self, checked: bool):
        t = self.locale.get
        self.server_toggle_btn.setText(t("stop_server_btn") if checked else t("start_server_btn"))
        self.server_toggle_btn.setToolTip(t("tooltip_stop_server") if checked else t("tooltip_start_server"))
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
        self.server_toggle_btn.setText(t("stop_server_btn"))
        self.status_bar.showMessage(t("server_running", port=self.port_input.text()))
        self.rail.status_badge.set_state("online", t("badge_server_running", port=self.port_input.text()))

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
        self.server_toggle_btn.setText(t("start_server_btn"))
        self.status_bar.showMessage(t("server_stopped"))
        self.rail.status_badge.set_state("offline", t("badge_server_stopped"))

    # ── log / client tracking ─────────────────────────────────

    def _append_log(self, msg: str):
        self.log_text.append(msg)

    def _on_client_connected(self, addr: str):
        self.clients_list.addItem(addr)
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
            "IDLE": t("socket_state_idle"),
            "TRANSFERRING": t("socket_state_transferring"),
        }
        self.socket_states_list.clear()
        for addr, state in self._socket_states.items():
            self.socket_states_list.addItem(f"{addr}  —  {state_labels.get(state, state)}")
            
        is_empty = len(self._socket_states) == 0
        self.socket_states_list.setVisible(not is_empty)
        self.states_empty.setVisible(is_empty)

    def _force_drop_client(self):
        item = self.clients_list.currentItem()
        if item:
            self.backend.force_disconnect_client(item.text())

    # ── user management ───────────────────────────────────────

    def _refresh_user_list(self):
        self.users_list.clear()
        users = self.auth.list_users()
        for name in users:
            self.users_list.addItem(name)
            
        is_empty = len(users) == 0
        self.users_list.setVisible(not is_empty)
        self.users_empty.setVisible(is_empty)

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
