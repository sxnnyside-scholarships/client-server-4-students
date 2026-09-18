"""
Module: sandbox_window.py
─────────────────────────
Purpose: Provides an integrated, split-screen self-study sandbox environment for students.

Architectural Role:
Acts as a composite UI container that embeds both the `ServerWindow` and `ClientWindow`
into a single dual-pane workspace separated by an interactive `QSplitter`. This provides
immediate cause-and-effect feedback for students working independently without requiring
multiple machine setups or manual window tiling.

Responsibilities:
- Instantiate and coordinate an embedded `ServerWindow` (left pane) and `ClientWindow` (right pane).
- Provide a top navigation bar with a single-click "Quick Connect" action for loopback testing.
- Pre-seed laboratory test credentials to eliminate authentication setup friction.
- Synchronize theme and locale changes across both embedded sub-windows.
- Gracefully tear down background threads and sockets when the sandbox window closes.

Dependencies:
- `PyQt6.QtWidgets.QMainWindow`, `QSplitter`
- `src.ui.client_window.ClientWindow`
- `src.ui.server_window.ServerWindow`
- `src.storage.auth.AuthManager`
- `src.storage.file_manager.FileManager`

Important Implementation Notes:
The sandbox binds to `127.0.0.1` (the IPv4 loopback interface). Because traffic never leaves
the host machine's kernel network stack, students can safely experiment with chaos controls
(latency, packet loss) and transport encryption (TLS) without impacting external networks.
"""

from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.config import ConfigManager
from src.localization.locale_manager import LocaleManager
from src.network.client_backend import ClientBackend
from src.network.server_backend import ServerBackend
from src.storage.auth import AuthManager
from src.storage.file_manager import FileManager
from src.ui.client_window import ClientWindow
from src.ui.icons.icon_provider import get_icon
from src.ui.server_window import ServerWindow
from src.ui.themes.theme_manager import ThemeManager
from src.ui.themes.tokens import icon_color, surface_colors, text_color
from src.ui.widgets.atoms import MintButton, MintIconButton


class SandboxWindow(QMainWindow):
    """
    Composite dual-pane window hosting synchronized Client and Server instances.

    ## Educational Note: The Loopback Interface & Self-Contained Labs
    The IP address `127.0.0.1` (IPv4 loopback / localhost) routes network packets entirely
    within the host operating system's TCP/IP stack without passing through physical network
    hardware. Embedding both ends of the socket in a split-screen view makes the Client-Server
    architecture immediately tangible: students click an action on the right pane and watch
    the corresponding TCP socket state, byte counters, and protocol telemetry animate on the left.

    Responsibilities:
    - Hosting the `QSplitter` layout.
    - Providing single-click loopback auto-connection.
    - Cleaning up server and client network loops on exit.
    """

    closed = pyqtSignal()

    def __init__(
        self,
        config: ConfigManager,
        locale: LocaleManager,
        themes: ThemeManager,
        app: QApplication,
        runtime=None,
    ):
        super().__init__()
        self.config = config
        self.locale = locale
        self.themes = themes
        self.app = app
        self.runtime = runtime
        self._theme_name = self.config.get("theme", "mint_light")

        # 1. Backends & Storage setup
        if self.runtime:
            auth_path = self.runtime.config_dir / "sandbox_users.json"
            sandbox_dir = self.runtime.sandboxes_dir / "self_study"
        else:
            from pathlib import Path

            auth_path = Path.home() / ".cs4s" / "sandbox_users.json"
            sandbox_dir = Path.home() / ".cs4s" / "sandboxes" / "self_study"

        self.auth = AuthManager(auth_path)
        # Guarantee pre-seeded student account has credentials student:student123
        self.auth.set_password("student", "student123")

        self.files = FileManager(sandbox_dir)
        self.server_backend = ServerBackend(self.auth, self.files, config=self.config)
        self.client_backend = ClientBackend()

        self.setMinimumSize(980, 600)
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            # On 16" displays (1728x1117+) and larger, comfortably expand to utilize screen real estate
            target_w = max(1360, min(1720, int(avail.width() * 0.94)))
            target_h = max(780, min(1020, int(avail.height() * 0.90)))
            self.resize(target_w, target_h)
        else:
            self.resize(1440, 860)

        self._build_ui()
        self._wire_signals()
        self.retranslate()

    def _build_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # ── Top Sandbox Bar ────────────────────────────────────
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        self.back_btn = MintIconButton("arrow-left", self._theme_name)
        header_bar.addWidget(self.back_btn)

        self.title_icon = QLabel()
        self.title_icon.setPixmap(get_icon("flask", icon_color(self._theme_name)).pixmap(QSize(20, 20)))
        header_bar.addWidget(self.title_icon)

        self.title_label = QLabel()
        self.title_label.setObjectName("sectionCardTitle")
        header_bar.addWidget(self.title_label)

        self.loopback_badge = QLabel()
        self.loopback_badge.setObjectName("badgePill")
        self.loopback_badge.setStyleSheet(
            f"background-color: {surface_colors(self._theme_name)['surface']}; "
            f"border: 1px solid {surface_colors(self._theme_name)['border']}; "
            f"color: {text_color(self._theme_name, 'muted')}; "
            "border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: 600;"
        )
        header_bar.addWidget(self.loopback_badge)

        header_bar.addStretch()

        self.quick_connect_btn = MintButton("", theme_name=self._theme_name)
        self.quick_connect_btn.setObjectName("primaryButton")
        self.quick_connect_btn.setIcon(get_icon("play", icon_color(self._theme_name, "on-accent")))
        self.quick_connect_btn.setIconSize(QSize(16, 16))
        header_bar.addWidget(self.quick_connect_btn)

        layout.addLayout(header_bar)

        # ── Dual Pane Splitter ─────────────────────────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # Left Pane: Server
        self.server_win = ServerWindow(
            self.config,
            self.locale,
            self.themes,
            self.app,
            auth=self.auth,
            files=self.files,
            backend=self.server_backend,
            runtime=self.runtime,
            embedded=True,
        )

        # Right Pane: Client
        self.client_win = ClientWindow(
            self.config,
            self.locale,
            self.themes,
            self.app,
            backend=self.client_backend,
            runtime=self.runtime,
            embedded=True,
        )

        # Pre-configure loopback defaults
        self.server_win.host_input.setText("127.0.0.1")
        self.server_win.port_input.setText("4500")

        self.client_win.host_input.setText("127.0.0.1")
        self.client_win.port_input.setText("4500")
        self.client_win.user_input.setText("student")
        self.client_win.pass_input.setText("student123")

        self.splitter.addWidget(self.server_win)
        self.splitter.addWidget(self.client_win)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        half_w = max(500, self.width() // 2)
        self.splitter.setSizes([half_w, half_w])

        layout.addWidget(self.splitter, 1)

    def _wire_signals(self):
        self.back_btn.clicked.connect(self.close)
        self.quick_connect_btn.clicked.connect(self._do_quick_connect)
        self.locale.locale_changed.connect(self.retranslate)

    def retranslate(self):
        t = self.locale.get
        self.setWindowTitle(t("sandbox.window_title"))
        self.title_label.setText(t("sandbox.window_title"))
        self.loopback_badge.setText(t("sandbox.loopback_badge"))
        self.quick_connect_btn.setText(t("sandbox.quick_connect"))
        self.quick_connect_btn.setToolTip(t("sandbox.quick_connect_tooltip"))
        self.back_btn.setToolTip(t("tooltip.back"))

    def _do_quick_connect(self):
        """
        Coordinates the startup of the local server and connects the client automatically.
        """
        # 1. Start server if not running
        if not self.server_backend.is_running:
            self.server_win._start_server()

        # 2. Wait 200ms for socket binding then connect client
        QTimer.singleShot(200, self._connect_client_now)

    def _connect_client_now(self):
        if not self.client_backend.is_connected:
            self.client_win._do_connect()

    def closeEvent(self, event):
        """
        Gracefully tears down network sockets before closing the window.
        """
        if self.client_backend.is_connected:
            self.client_backend.disconnect()
        if self.server_backend.is_running:
            self.server_backend.stop()
        self.closed.emit()
        event.accept()
