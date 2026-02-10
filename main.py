"""
Client-Server 4 Students — Main Entry Point
────────────────────────────────────────────
Run this file to launch the application:

    python main.py

The Launcher window will open, allowing you to choose
between Client mode and Server mode.
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

# Ensure the project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import ConfigManager
from src.localization.locale_manager import LocaleManager
from src.ui.launcher import LauncherWindow
from src.ui.themes.theme_manager import ThemeManager


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Client-Server 4 Students")
    app.setApplicationVersion("1.0.0")

    # Initialise core subsystems
    config = ConfigManager(PROJECT_ROOT / "config" / "settings.json")
    locale = LocaleManager(PROJECT_ROOT / "src" / "localization")
    themes = ThemeManager(PROJECT_ROOT / "src" / "ui" / "themes")

    # Apply saved preferences
    locale.set_locale(config.get("locale", "en"))
    themes.apply_theme(app, config.get("theme", "mint_light"))

    # Show the Launcher
    launcher = LauncherWindow(config, locale, themes, app)
    launcher.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
