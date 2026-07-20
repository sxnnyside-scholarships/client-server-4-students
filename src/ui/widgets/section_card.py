"""
Module: section_card.py
────────────────────────
Purpose: MintPy's content panel — a softly rounded card with a colored left
accent bar and a gentle mint-tinted shadow, replacing the generic
`QGroupBox` default look.

Architectural Role:
The shape every primary content panel in CS4S shares: generous rounded
corners (fresh, calm, easy on the eyes over long sessions — never a harsh
rectangle), a 3px accent bar on the left edge (mint for primary panels,
"sage" for Lab View / advanced panels), and a soft color-tinted shadow
standing in for a flat 1px border as the panel's depth cue.

Responsibilities:
- Painting its own rounded background, border, and accent bar.
- Hosting an uppercase title and an arbitrary content layout.

Expected Collaborators:
- `src.ui.client_window`, `src.ui.server_window` (compose their panels
  from this instead of `QGroupBox`).
"""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget

from src.ui.themes.tokens import sage_color, surface_colors, RADIUS, accent_color

_CARD_RADIUS = RADIUS["lg"]
ACCENT_BAR_WIDTH = 3


class SectionCard(QWidget):
    """
    A softly rounded content panel with a colored left accent bar.

    Why it exists:
    A calm, rounded surface reads as approachable and fresh — the "mint"
    half of MintPy's identity — without resorting to sharp geometric
    gimmicks. The accent bar is the one consistent, ownable marker that a
    panel belongs to CS4S, reused everywhere a panel exists.

    Responsibilities:
    - Custom-painting the rounded background, border, and accent bar.
    - Exposing `content_layout` for callers to populate like any QVBoxLayout.
    - Applying a soft, accent-tinted drop shadow instead of relying on the
      border alone for depth.

    Non-Responsibilities (Anti-Goals):
    - It does NOT manage the widgets placed inside it — callers own that.
    """

    def __init__(self, theme_name: str, accent: str = "mint", parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self._accent = accent
        colors = surface_colors(theme_name)
        self._surface = QColor(colors["surface"])
        self._border = QColor(colors["border"])
        self._accent_color = QColor(
            sage_color(theme_name) if accent == "sage" else accent_color(theme_name)
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(ACCENT_BAR_WIDTH + 13, 16, 16, 14)
        outer.setSpacing(8)

        self._title_label = QLabel()
        self._title_label.setObjectName("sectionCardTitle")
        self._title_label.setStyleSheet(
            f"color: {self._accent_color.name()}; font-weight: 700; "
            "font-size: 11px; background: transparent;"
        )
        outer.addWidget(self._title_label)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(self.content_layout, 1)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        glow = QColor(self._accent_color)
        glow.setAlpha(45)
        shadow.setColor(glow)
        self.setGraphicsEffect(shadow)

    def set_title(self, text: str):
        """
        Sets the panel's uppercase header label.

        Args:
            text: The (already localized) title string.

        Returns:
            None.

        Side Effects:
            Mutates the title label's text.

        Failure Behavior:
            None.
        """
        self._title_label.setText(text.upper())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, _CARD_RADIUS, _CARD_RADIUS)

        painter.fillPath(path, self._surface)
        painter.setPen(QPen(self._border, 1))
        painter.drawPath(path)

        accent_rect = QRectF(
            rect.left(), rect.top() + _CARD_RADIUS,
            ACCENT_BAR_WIDTH, rect.height() - 2 * _CARD_RADIUS,
        )
        painter.fillRect(accent_rect, self._accent_color)
