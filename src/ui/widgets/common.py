"""
Module: common.py
─────────────────
Purpose: Provides reusable, self-contained UI components shared across the application.

Architectural Role:
Acts as a standardized component library. It reduces code duplication in the main
window classes by centralizing the layout and styling of repeated elements.

Responsibilities:
- Provide the `BrandingFooter` widget.
- Provide the `LabeledInput` widget.
- Provide the `StatusBadge` widget (live connection/server state pill).
- Provide formatting utilities like `format_file_size`.

Expected Collaborators:
- `src.ui.launcher`, `src.ui.client_window`, `src.ui.server_window`
- `src.ui.widgets.nav_rail.NavRail` (hosts `StatusBadge` and `BrandingFooter`)
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QWidget

from src.ui.themes.tokens import status_color
from src.ui.widgets.atoms import MintTextInput


def format_file_size(size_bytes: int) -> str:
    """
    Converts a raw byte count into a human-readable string (KB, MB, GB).

    Args:
        size_bytes: The integer number of bytes to format.

    Returns:
        A formatted string with the appropriate suffix.

    Side Effects:
        None.

    Failure Behavior:
        None.
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**2):.1f} MB"
    return f"{size_bytes / (1024**3):.1f} GB"


class BrandingFooter(QLabel):
    """
    A subtle, single-line attribution footer displayed at the bottom of every
    main window.

    Why it exists:
    CS4S is a Sxnnyside Scholarships product; every screen carries a quiet,
    non-interactive attribution line so the whole application reads as one
    coherent product rather than a bare student exercise — without turning
    the footer into a promotional link.

    Responsibilities:
    - Rendering the footer text.
    - Providing an update method for dynamic language switching.

    Non-Responsibilities (Anti-Goals):
    - It does NOT track telemetry, open URLs, or report clicks.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("brandingFooter")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def update_text(self, text: str):
        """
        Public API used by `retranslate()` in each window to update the text.

        Args:
            text: The translated attribution string.

        Returns:
            None.

        Side Effects:
            Mutates the widget's text.

        Failure Behavior:
            None.
        """
        self.setText(text)


class LabeledInput(QWidget):
    """
    A composite widget combining a `QLabel` and a `QLineEdit` horizontally.

    Why it exists:
    Forms in PyQt often require pairing a label with an input. This widget bundles
    them together to reduce boilerplate layout code in parent windows.

    Responsibilities:
    - Wrapping a `QLabel` and `QLineEdit` in a horizontal layout.
    - Exposing text getters and setters.

    Non-Responsibilities (Anti-Goals):
    - It does NOT perform input validation (e.g., checking if it's an integer).
    """

    def __init__(self, label_text: str = "", placeholder: str = "", theme_name: str = "mint_light", parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = QLabel(label_text)
        self.label.setMinimumWidth(60)
        self.input = MintTextInput(self._theme_name)
        self.input.setPlaceholderText(placeholder)

        layout.addWidget(self.label)
        layout.addWidget(self.input)

    def text(self) -> str:
        return self.input.text().strip()

    def set_text(self, value: str):
        self.input.setText(value)


class StatusBadge(QWidget):
    """
    A small, always-visible pill showing the current connection/server state.

    Why it exists:
    Both the Client and Server windows previously had no persistent visual
    indicator of live state — the only feedback was a transient status-bar
    message that disappears after a few seconds, leaving the idle screen
    looking inert. This badge stays on screen and updates in place, using
    color (not just text) to communicate state at a glance.

    Responsibilities:
    - Rendering a colored dot + label reflecting the current state.
    - Exposing `set_state()` so windows can drive it from their own signals.

    Non-Responsibilities (Anti-Goals):
    - It does NOT decide what the current state is — the owning window
      determines that from its backend signals and calls `set_state()`.
    """

    def __init__(self, theme_name: str, parent=None):
        super().__init__(parent)
        self._theme_name = theme_name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)
        glow = QGraphicsDropShadowEffect(self._dot)
        glow.setBlurRadius(10)
        glow.setXOffset(0)
        glow.setYOffset(0)
        self._glow = glow
        self._dot.setGraphicsEffect(glow)
        self._label = QLabel()
        self._label.setObjectName("statusBadgeLabel")

        layout.addWidget(self._dot)
        layout.addWidget(self._label)

        self.set_state("offline", "")

    def set_state(self, state: str, text: str):
        """
        Updates the badge's color and text to reflect a new state.

        Args:
            state: One of "offline", "connecting", "online", "error" — see
                `tokens.STATUS_COLORS`.
            text: The localized label to display next to the dot.

        Returns:
            None.

        Side Effects:
            Mutates the dot's stylesheet color and the label's text.

        Failure Behavior:
            Falls back to the "offline" color if `state` is unrecognized.
        """
        color = status_color(self._theme_name, state)
        self._dot.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
        glow_color = QColor(color)
        glow_color.setAlpha(180)
        self._glow.setColor(glow_color)
        self._label.setText(text)
