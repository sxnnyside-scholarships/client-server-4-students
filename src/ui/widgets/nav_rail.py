"""
Module: nav_rail.py
────────────────────
Purpose: The persistent left sidebar shell shared by the Client and Server
windows — brand mark, live status badge, connection/server controls, and a
mode switcher (Files / Lab View) that replaces the window's central content
instead of squeezing it inside a splitter.

Architectural Role:
Both `ClientWindow` and `ServerWindow` compose their primary chrome from this
rail rather than a horizontal top toolbar. This is the structural change
that makes "everything looks the same" and "Lab View crushes the rest of
the UI" impossible: the rail is a fixed, generously-proportioned column,
and switching modes swaps the *entire* central widget rather than resizing
one panel among several.

Responsibilities:
- Rendering the brand mark (a mint leaf mark — MintPy's one literal nod to
  "mint" as the fresh herb, not just a color), an always-visible
  `StatusBadge`, a caller-populated form region, and the mode-switch nav
  items.
- Painting its own background and a signature soft mint gradient seam on
  its right edge, replacing a flat 1px border.
- Exposing an exclusive `mode_changed(str)` signal driven by the nav items.
- Animating the active nav item's highlight in with a brief, subtle fade
  rather than snapping instantly — motion should feel calm, not flashy.

Expected Collaborators:
- `src.ui.client_window.ClientWindow`, `src.ui.server_window.ServerWindow`.
- `src.ui.widgets.common.StatusBadge`.
"""

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QLinearGradient, QPainter
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.icons.icon_provider import get_icon
from src.ui.themes.tokens import icon_color, mint_gradient, surface_colors
from src.ui.widgets.common import BrandingFooter, StatusBadge

RAIL_WIDTH = 252


class _NavItemButton(QPushButton):
    """A checkable rail entry; its active state fades in as a soft mint
    gradient pill (150ms, calm ease-out) rather than snapping instantly —
    the one deliberately animated moment in the rail."""

    def __init__(self, theme_name: str, icon_name: str, parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self.setCheckable(True)
        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icon_name = icon_name
        self.setIcon(get_icon(icon_name, icon_color(theme_name)))
        self._base_style = (
            "QPushButton { text-align: left; padding-left: 12px; "
            "border: none; background: transparent; font-weight: 600; "
            "font-size: 13px; }"
        )
        self.setStyleSheet(self._base_style)

        self._highlight = 0.0
        self._anim = QPropertyAnimation(self, b"highlight", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.toggled.connect(self._on_toggled)

    def _get_highlight(self):
        return self._highlight

    def _set_highlight(self, value):
        self._highlight = value
        self.update()

    highlight = pyqtProperty(float, _get_highlight, _set_highlight)

    def _on_toggled(self, checked: bool):
        role = "on-accent" if checked else "default"
        self.setIcon(get_icon(self._icon_name, icon_color(self._theme_name, role)))
        self.setStyleSheet(
            self._base_style.replace(
                "font-size: 13px;",
                f"font-size: 13px; color: {'#FFFFFF' if checked else ''};",
            )
        )
        self._anim.stop()
        self._anim.setStartValue(self._highlight)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event):
        if self._highlight > 0.0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(self.rect()).adjusted(0, 2, 0, -2)
            soft, deep = mint_gradient(self._theme_name)
            gradient = QLinearGradient(rect.topLeft(), rect.topRight())
            gradient.setColorAt(0.0, QColor(soft))
            gradient.setColorAt(1.0, QColor(deep))
            painter.setOpacity(self._highlight)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect, 10, 10)
            painter.end()
        super().paintEvent(event)


class NavRail(QWidget):
    """
    The fixed-width sidebar shell shared by the Client and Server windows.

    Why it exists:
    Replaces the previous horizontal top toolbar (host/port fields, action
    buttons, and the Lab View toggle all crammed into one row with no
    hierarchy) with a real navigation surface: identity at the top, live
    state always visible, primary controls grouped, and mode-switching
    treated as first-class navigation rather than a checkbox.

    Responsibilities:
    - Owning the brand mark, status badge, and footer.
    - Exposing `form_layout` for the owning window's connection/server form.
    - Exposing `add_mode` to register mutually-exclusive content modes and
      emitting `mode_changed` when the user switches between them.

    Non-Responsibilities (Anti-Goals):
    - It does NOT know what the modes contain — the owning window supplies
      and swaps the actual content widgets.
    """

    mode_changed = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self, theme_name: str, parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self.setFixedWidth(RAIL_WIDTH)
        colors = surface_colors(theme_name)
        self._bg = QColor(colors["surface"])
        soft, deep = mint_gradient(theme_name)
        self._seam_soft = QColor(soft)
        self._seam_deep = QColor(deep)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 20, 15, 16)
        outer.setSpacing(18)

        # ── brand mark: just the text and the gradient seam ────
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(12, 16, 12, 24)
        brand_row.setSpacing(12)

        self._logo_icon = QLabel()
        self._logo_icon.setPixmap(get_icon("server", icon_color(self._theme_name, "default")).pixmap(QSize(28, 28)))
        brand_row.addWidget(self._logo_icon)

        self._wordmark = QLabel("CS4S")
        self._wordmark.setObjectName("navWordmark")
        # Ensure it has a prominent, modern look overriding default QSS if needed
        soft, deep = mint_gradient(theme_name)
        self._wordmark.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: 800;
                letter-spacing: -0.5px;
                color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {soft}, stop:1 {deep});
            }}
        """)
        brand_row.addWidget(self._wordmark)
        brand_row.addStretch()
        outer.addLayout(brand_row)

        # ── live status ──────────────────────────────────────
        self.status_badge = StatusBadge(theme_name)
        outer.addWidget(self.status_badge)

        self.form_layout = QVBoxLayout()
        self.form_layout.setSpacing(16)
        outer.addLayout(self.form_layout)

        # ── mode switch ───────────────────────────────────────
        self._nav_label = QLabel()
        self._nav_label.setObjectName("navSectionLabel")
        outer.addWidget(self._nav_label)

        self.nav_layout = QVBoxLayout()
        self.nav_layout.setSpacing(2)
        outer.addLayout(self.nav_layout)
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        outer.addStretch(1)

        self.back_btn = QPushButton()
        self.back_btn.setIcon(get_icon("arrow-left", icon_color(theme_name)))
        self.back_btn.clicked.connect(self.back_requested.emit)
        outer.addWidget(self.back_btn)

        self.footer = BrandingFooter()
        outer.addWidget(self.footer)

    def set_nav_section_label(self, text: str):
        self._nav_label.setText(text.upper())

    def add_mode(self, mode_id: str, icon_name: str, label: str, checked: bool = False) -> _NavItemButton:
        """
        Registers a content mode as a nav rail entry.

        Args:
            mode_id: The identifier emitted by `mode_changed` when selected.
            icon_name: The MintPy icon shown next to the label.
            label: The (already localized) entry text.
            checked: Whether this entry starts selected.

        Returns:
            The created nav item button, in case the caller needs to
            re-translate its text later.

        Side Effects:
            Adds the button to the rail's layout and exclusive group.

        Failure Behavior:
            None.
        """
        btn = _NavItemButton(self._theme_name, icon_name)
        btn.setText(f"  {label}")
        if checked:
            btn.setChecked(True)
        btn.toggled.connect(lambda on, m=mode_id: on and self.mode_changed.emit(m))
        self._nav_group.addButton(btn)
        self.nav_layout.addWidget(btn)
        return btn

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self._bg)

        # Signature gradient seam — the rail's right edge, replacing a flat
        # 1px border with MintPy's soft-to-deep mint identity gradient.
        seam = QRectF(self.width() - 3, 0, 3, self.height())
        gradient = QLinearGradient(seam.topLeft(), seam.bottomLeft())
        gradient.setColorAt(0.0, self._seam_soft)
        gradient.setColorAt(1.0, self._seam_deep)
        painter.fillRect(seam, gradient)
