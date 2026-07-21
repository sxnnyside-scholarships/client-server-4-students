"""
Module: launcher.py
───────────────────
Purpose: Provides the initial entry point window for the CS4S application.

Architectural Role:
Acts as the central Dependency Injection hub and Application Bootstrapper.
It instantiates the shared singletons (Locale, Theme, Runtime) and injects
them into either the Client or Server window based on user selection.

Responsibilities:
- Render the start screen (Client vs. Server choice).
- Allow the user to change global language and theme settings before booting an engine.
- Instantiate and launch the selected child window, hiding itself until the child closes.

Expected Collaborators:
- `src.main` (invokes this class).
- `src.ui.client_window` (instantiated here).
- `src.ui.server_window` (instantiated here).
"""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.core.config import ConfigManager
from src.localization.locale_manager import LocaleManager
from src.ui.icons.icon_provider import get_icon
from src.ui.themes.theme_manager import ThemeManager
from src.ui.themes.tokens import icon_color
from src.ui.widgets.common import BrandingFooter
from src.ui.widgets.atoms import MintModeCard, MintDropdown


class LauncherWindow(QWidget):
    """
    Start screen and Dependency Injection container.

    Why it exists:
    Because CS4S bundles both the client and server into a single executable,
    there needs to be an initial routing screen. The launcher serves this purpose
    while also acting as the top-level owner of global configurations.

    Responsibilities:
    - Bootstrapping the `ClientBackend` or `ServerBackend` with necessary dependencies.
    - Swapping the active `QMainWindow` while keeping the Qt Event Loop alive.

    Non-Responsibilities (Anti-Goals):
    - It does NOT start any network sockets itself.
    - It does NOT parse command-line arguments.
    """

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
        self._child_window = None

        self.setMinimumSize(520, 430)
        self._build_ui()
        self._wire_signals()
        self.retranslate()

        self.locale.locale_changed.connect(self.retranslate)

    # ── UI construction ───────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(32, 24, 32, 20)

        # ── header: title + subtitle, compact ─────────────────
        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.title_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitleLabel")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.subtitle_label)

        # ── mode selection: two compact cards, side by side ───
        neutral = icon_color(self._theme_name)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        self.client_btn = self._make_mode_card("connect", neutral)
        self.server_btn = self._make_mode_card("server", neutral)
        cards_row.addWidget(self.client_btn, 1)
        cards_row.addWidget(self.server_btn, 1)
        root.addLayout(cards_row)

        root.addStretch()

        root.addStretch()

        # ── settings: inline row, not a tall stacked column ───
        settings_row = QHBoxLayout()
        settings_row.setSpacing(20)

        self.lang_label = QLabel()
        self.lang_label.setObjectName("settingsLabel")
        self.lang_combo = MintDropdown(self._theme_name)

        lang_col = QVBoxLayout()
        lang_col.setSpacing(2)
        lang_col.addWidget(self.lang_label)
        lang_col.addWidget(self.lang_combo)

        self.theme_label = QLabel()
        self.theme_label.setObjectName("settingsLabel")
        self.theme_combo = MintDropdown(self._theme_name)

        theme_col = QVBoxLayout()
        theme_col.setSpacing(2)
        theme_col.addWidget(self.theme_label)
        theme_col.addWidget(self.theme_combo)

        settings_row.addLayout(lang_col, 1)
        settings_row.addLayout(theme_col, 1)
        root.addLayout(settings_row)

        # ── footer: version + attribution on one compact line ─
        self.version_label = QLabel()
        self.version_label.setObjectName("versionLabel")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.version_label)

        self.footer = BrandingFooter()
        root.addWidget(self.footer)

    def _make_mode_card(self, icon_name: str, color: str) -> MintModeCard:
        """
        Builds one of the two Launcher mode-selection cards (Client/Server).

        Args:
            icon_name: The MintPy icon to display above the card's label.
            color: The icon tint color for the current theme.

        Returns:
            A configured `QToolButton` styled as a `modeCard` (see the QSS
            `QToolButton#modeCard` rules) with the icon stacked above the
            text — a compact card, not a full-width bar.

        Side Effects:
            None.

        Failure Behavior:
            None.
        """
        btn = MintModeCard(theme_name=self._theme_name)
        btn.setObjectName("modeCard")
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn.setIcon(get_icon(icon_name, color))
        btn.setIconSize(QSize(28, 28))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(88)
        return btn

    # ── signals ───────────────────────────────────────────────

    def _wire_signals(self):
        self.client_btn.clicked.connect(self._open_client)
        self.server_btn.clicked.connect(self._open_server)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)

    # ── i18n ──────────────────────────────────────────────────

    def retranslate(self):
        t = self.locale.get
        self.setWindowTitle(t("launcher.app_title"))
        self.title_label.setText(t("launcher.app_title"))
        self.subtitle_label.setText(t("launcher.welcome"))
        self.client_btn.setText(t("launcher.start_client"))
        self.server_btn.setText(t("launcher.start_server"))
        self.client_btn.set_description(t("launcher.start_client_desc"))
        self.server_btn.set_description(t("launcher.start_server_desc"))
        self.client_btn.setToolTip(t("tooltip.connect"))
        self.server_btn.setToolTip(t("tooltip.start_server"))

        self.lang_label.setText(t("launcher.language"))
        self.lang_combo.setItemText(1, t("launcher.lang_es"))

        self.adjustSize()
        self.theme_label.setText(t("launcher.theme"))
        self.version_label.setText(t("launcher.version_label"))

        self.footer.update_text(t("common.footer_prefix"))

        # Rebuild theme combo with translated names
        current = self.config.get("theme", "mint_light")
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self.theme_combo.addItem(t("launcher.theme_light"), "mint_light")
        self.theme_combo.addItem(t("launcher.theme_dark"), "mint_dark")
        idx = self.theme_combo.findData(current)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)

        # Rebuild lang combo
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()

        from src.localization.locale_manager import LocaleManager

        current_lang = self.locale.current_locale
        idx = 0
        for i, (code, name) in enumerate(LocaleManager.SUPPORTED_LOCALES.items()):
            self.lang_combo.addItem(name, code)
            if code == current_lang:
                idx = i

        self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.blockSignals(False)

    # ── slots ─────────────────────────────────────────────────

    def _on_lang_changed(self):
        code = self.lang_combo.currentData()
        if code:
            self.config.set("locale", code)
            self.locale.set_locale(code)

    def _on_theme_changed(self):
        name = self.theme_combo.currentData()
        if name:
            self.config.set("theme", name)
            self.themes.apply_theme(self.app, name)

    def _open_client(self):
        from src.ui.client_window import ClientWindow
        from src.network.client_backend import ClientBackend

        backend = ClientBackend()

        self.hide()
        self._child_window = ClientWindow(
            self.config, self.locale, self.themes, self.app, backend=backend, runtime=self.runtime
        )
        self._child_window.closed.connect(self._on_child_closed)
        self._child_window.showMaximized()

    def _open_server(self):
        from src.ui.server_window import ServerWindow
        from src.network.server_backend import ServerBackend
        from src.storage.auth import AuthManager
        from src.storage.file_manager import FileManager

        auth = AuthManager(self.runtime.config_dir / "users.json")
        files = FileManager(self.runtime.sandboxes_dir)
        backend = ServerBackend(auth, files, config=self.config)

        self.hide()
        self._child_window = ServerWindow(
            self.config,
            self.locale,
            self.themes,
            self.app,
            auth=auth,
            files=files,
            backend=backend,
            runtime=self.runtime,
        )
        self._child_window.closed.connect(self._on_child_closed)
        self._child_window.showMaximized()

    def _on_child_closed(self):
        self._child_window = None
        self.show()
