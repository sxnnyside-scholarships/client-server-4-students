"""
Package: src.ui.themes
──────────────────────
Purpose: Provides QSS (Qt Style Sheet) management and dynamic visual theming capabilities.

Architectural Role:
Acts as the styling engine. It isolates visual design constants (colors, margins, borders)
from the functional Python UI logic, ensuring the application can be visually rebranded
without modifying core source code.

Responsibilities:
- Load `.qss` files from disk dynamically.
- Apply system-wide stylesheets to the active `QApplication`.

Public API:
- `theme_manager.ThemeManager`: The core styling singleton used to switch visual themes.

Expected Collaborators:
- `src.ui.launcher`: Consumed to let the user select themes at startup.
- `src.core.config`: Consumed to save the user's selected theme string.
"""
