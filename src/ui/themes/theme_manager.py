"""
Module: theme_manager.py
────────────────────────
Purpose: Loads QSS stylesheets and applies them to the application dynamically.

Architectural Role:
Acts as the central styling orchestrator. It completely separates the visual design
from the functional Python code, allowing the GUI to be rebranded or switched into
"Dark Mode" without rebuilding or modifying the Qt layout structures.

Responsibilities:
- Resolve paths to `.qss` (Qt Style Sheet) files bundled with the application.
- Apply the stylesheets directly to the global `QApplication` instance.

Expected Collaborators:
- `src.ui.launcher.LauncherWindow` (provides the UI dropdown to switch themes)
- `src.core.config` (persists the user's selected theme)
"""

from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.ui.themes.tokens import PALETTES


class ThemeManager:
    """
    Handles loading and applying QSS themes to the running application.

    Why it exists:
    Provides a standardized way to read CSS-like syntax from disk and inject it into
    the active Qt event loop, ensuring that all windows inherit the same visual design.

    Responsibilities:
    - Mapping theme string identifiers to `.qss` filenames.
    - Reading stylesheet files from disk safely.

    Non-Responsibilities (Anti-Goals):
    - It does NOT define the colors itself (those are in the `.qss` files).
    - It does NOT persist the user's choice to `config.json` (delegated to the UI).
    """

    THEMES = {
        "mint_light": "mint_light",
        "mint_dark": "mint_dark",
    }

    def __init__(self, themes_dir: str | Path):
        self.themes_dir = Path(themes_dir)

    def apply_theme(self, app: QApplication, theme_name: str):
        """
        Loads a QSS file from disk and applies it globally to the PyQt application.

        Args:
            app: The running `QApplication` singleton.
            theme_name: The string identifier of the theme (e.g., 'mint_dark').

        Returns:
            None.

        Side Effects:
            Mutates the global visual state of the entire `QApplication`.
            Reads data from the host filesystem.

        Failure Behavior:
            If the requested theme is invalid, it defaults to 'mint_light.qss'.
            If the QSS file is missing from disk, it clears the application stylesheet.
        """
        theme_id = self.THEMES.get(theme_name, "mint_light")
        qss_path = self.themes_dir / "base.template.qss"
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as fh:
                template = fh.read()

            palette = PALETTES.get(theme_id, PALETTES["mint_light"])
            for var, color in palette.items():
                template = template.replace(var, color)

            app.setStyleSheet(template)
        else:
            app.setStyleSheet("")

    def available_themes(self) -> list[str]:
        """
        Retrieves the string identifiers for all bundled themes.

        Args:
            None.

        Returns:
            A list of string keys representing the available themes.

        Side Effects:
            None.

        Failure Behavior:
            None.
        """
        return list(self.THEMES.keys())
