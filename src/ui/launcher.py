"""
Launcher Window
───────────────
The main entry point of the application.
Lets the user pick Client or Server mode, language, and theme.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.config import ConfigManager
from src.localization.locale_manager import LocaleManager
from src.ui.themes.theme_manager import ThemeManager
from src.ui.widgets.common import BrandingFooter


class LauncherWindow(QWidget):
    """Start screen — choose Client or Server."""

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
        self._child_window = None

        self.setFixedSize(460, 510)
        self._build_ui()
        self._wire_signals()
        self.retranslate()

        self.locale.locale_changed.connect(self.retranslate)

    # ── UI construction ───────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(44, 32, 44, 28)

        # Title
        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.title_label)

        # Subtitle
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitleLabel")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.subtitle_label)

        root.addSpacing(24)

        # Action buttons
        self.client_btn = QPushButton()
        self.client_btn.setObjectName("primaryButton")
        self.client_btn.setMinimumHeight(50)
        self.client_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        root.addWidget(self.client_btn)

        self.server_btn = QPushButton()
        self.server_btn.setObjectName("primaryButton")
        self.server_btn.setMinimumHeight(50)
        self.server_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        root.addWidget(self.server_btn)

        root.addSpacing(24)

        # ── settings column ──────────────────────────────────
        settings = QVBoxLayout()
        settings.setSpacing(4)

        self.lang_label = QLabel()
        self.lang_label.setObjectName("settingsLabel")
        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(220)
        for code, name in LocaleManager.SUPPORTED_LOCALES.items():
            self.lang_combo.addItem(name, code)
        idx = self.lang_combo.findData(self.config.get("locale", "en"))
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)

        self.theme_label = QLabel()
        self.theme_label.setObjectName("settingsLabel")
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(220)
        # Items populated in retranslate() so labels are localised

        settings.addWidget(self.lang_label)
        settings.addWidget(self.lang_combo)
        settings.addSpacing(12)
        settings.addWidget(self.theme_label)
        settings.addWidget(self.theme_combo)

        settings_wrapper = QHBoxLayout()
        settings_wrapper.addStretch()
        settings_wrapper.addLayout(settings)
        settings_wrapper.addStretch()

        root.addLayout(settings_wrapper)
        root.addStretch()

        # Version
        self.version_label = QLabel()
        self.version_label.setObjectName("versionLabel")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.version_label)

        # Branding footer
        self.footer = BrandingFooter()
        root.addWidget(self.footer)

    # ── signals ───────────────────────────────────────────────

    def _wire_signals(self):
        self.client_btn.clicked.connect(self._open_client)
        self.server_btn.clicked.connect(self._open_server)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)

    # ── i18n ──────────────────────────────────────────────────

    def retranslate(self):
        t = self.locale.get
        self.setWindowTitle(t("app_title"))
        self.title_label.setText(t("app_title"))
        self.subtitle_label.setText(t("welcome"))
        self.client_btn.setText(t("start_client"))
        self.server_btn.setText(t("start_server"))
        self.lang_label.setText(t("language"))
        self.theme_label.setText(t("theme"))
        self.version_label.setText(t("version_label"))

        self.footer.update_text(t("footer_prefix"), t("footer_link"))

        # Rebuild theme combo with translated names
        current = self.config.get("theme", "mint_light")
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self.theme_combo.addItem(t("theme_light"), "mint_light")
        self.theme_combo.addItem(t("theme_dark"), "mint_dark")
        idx = self.theme_combo.findData(current)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)

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

        self.hide()
        self._child_window = ClientWindow(
            self.config, self.locale, self.themes, self.app
        )
        self._child_window.closed.connect(self._on_child_closed)
        self._child_window.show()

    def _open_server(self):
        from src.ui.server_window import ServerWindow

        self.hide()
        self._child_window = ServerWindow(
            self.config, self.locale, self.themes, self.app
        )
        self._child_window.closed.connect(self._on_child_closed)
        self._child_window.show()

    def _on_child_closed(self):
        self._child_window = None
        self.show()
