"""
Module: main.py
───────────────
Purpose: The primary entry point for launching the CS4S application.

Architectural Role:
Acts as the root bootstrapper. It initializes the Qt Application event loop,
resolves the runtime environment (portable vs OS-native), instantiates core
managers (Config, Locale, Theme), and launches the `LauncherWindow`.

Responsibilities:
- Resolve Qt platform plugin paths to prevent runtime crashes.
- Bootstrap the `RuntimeEnvironment` and migrate legacy data if necessary.
- Inject initialized dependencies into the `LauncherWindow`.
- Block the main thread via `app.exec()`.

Expected Collaborators:
- `PyQt6` (GUI framework).
- `src.core.runtime.RuntimeEnvironment` (provides OS paths).
- `src.ui.launcher.LauncherWindow` (the first UI screen).
"""

import os
import sys
from pathlib import Path
from PyQt6.QtCore import QLibraryInfo

os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)

from PyQt6.QtWidgets import QApplication

# Ensure the project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))  # noqa: E402

from src.core.config import ConfigManager  # noqa: E402
from src.core.runtime import RuntimeEnvironment  # noqa: E402
from src.localization.locale_manager import LocaleManager  # noqa: E402
from src.ui.launcher import LauncherWindow  # noqa: E402
from src.ui.themes.theme_manager import ThemeManager  # noqa: E402


def main():
    """
    Initializes and executes the CS4S desktop application.

    Args:
        None.

    Returns:
        None (exits the Python process with the Qt exit code).

    Side Effects:
        Spawns the Qt Event Loop.
        Reads and writes configuration files to the disk via `RuntimeEnvironment`.

    Failure Behavior:
        Crashes if the Qt libraries are missing or incompatible.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Client-Server 4 Students")
    app.setApplicationVersion("1.0.0")

    # Initialize runtime environment
    runtime = RuntimeEnvironment(PROJECT_ROOT)
    runtime.bootstrap()

    # Initialise core subsystems using runtime paths
    config = ConfigManager(runtime.config_dir / "settings.json")
    locale = LocaleManager(runtime.locales_dir)
    themes = ThemeManager(runtime.themes_dir)

    # Apply saved preferences
    locale.set_locale(config.get("locale", "en"))
    themes.apply_theme(app, config.get("theme", "mint_light"))

    # Show the Launcher
    launcher = LauncherWindow(config, locale, themes, app, runtime=runtime)
    launcher.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
