"""
Theme Manager
─────────────
Loads QSS stylesheets and applies them to the running QApplication
so every widget picks up the new look instantly.
"""

from pathlib import Path

from PyQt6.QtWidgets import QApplication


class ThemeManager:
    """Handles loading and applying QSS themes."""

    THEMES = {
        "mint_light": "mint_light.qss",
        "mint_dark": "mint_dark.qss",
    }

    def __init__(self, themes_dir: str | Path):
        self.themes_dir = Path(themes_dir)

    def apply_theme(self, app: QApplication, theme_name: str):
        """Load a QSS file and apply it to *app*."""
        filename = self.THEMES.get(theme_name, "mint_light.qss")
        qss_path = self.themes_dir / filename
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as fh:
                app.setStyleSheet(fh.read())
        else:
            app.setStyleSheet("")

    def available_themes(self) -> list[str]:
        """Return the list of available theme keys."""
        return list(self.THEMES.keys())
