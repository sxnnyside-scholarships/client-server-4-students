"""
Module: toggle_button.py
─────────────────────────
Purpose: A single checkable button representing a binary lifecycle action
(currently: Start/Stop Server), replacing two separate buttons that visually
compete for the same space and attention.

Architectural Role:
`ServerWindow` previously placed `start_btn` and `stop_btn` side by side,
both sized and styled almost identically, with only `.setEnabled()`
toggling which one was clickable — the user has to read both labels to
figure out which one is "live." `ToggleActionButton` collapses that into
one control whose color and icon *are* the state.

Responsibilities:
- Rendering the "off" state as a primary/mint action (safe to start).
- Rendering the "on" state as a danger/red action (stopping is disruptive —
  it drops every connected client).
- Exposing `set_checked_silently()` so the owning window can sync the
  button to the real backend state without re-triggering `toggled`.

Expected Collaborators:
- `src.ui.server_window.ServerWindow`.
"""

from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QWidget

from src.ui.widgets.atoms import MintButton

from src.ui.icons.icon_provider import get_icon
from src.ui.themes.tokens import icon_color


class ToggleActionButton(MintButton):
    """
    A checkable button whose object name (and therefore QSS styling) flips
    between `toggleActionOff` and `toggleActionOn` states.

    Why it exists:
    See module docstring — this is the fix for "two buttons of equal visual
    weight fighting for the same space" (RIQA/design feedback point 4).

    Responsibilities:
    - Swapping icon + object name on toggle.
    - Re-applying its stylesheet on state change (Qt requires an explicit
      unpolish/polish cycle for QSS object-name selectors to re-evaluate).

    Non-Responsibilities (Anti-Goals):
    - It does NOT decide *when* to flip — the owning window still listens
      to the real backend signals (`server_started`/`server_stopped`) and
      calls `set_checked_silently()`, so the button never lies about state
      if a start/stop fails.
    """

    def __init__(
        self,
        theme_name: str,
        icon_off: str,
        icon_on: str,
        parent: QWidget | None = None,
    ):
        super().__init__("", theme_name, parent)
        self._theme_name = theme_name
        self._icon_off = icon_off
        self._icon_on = icon_on
        self.setCheckable(True)
        self.setIconSize(QSize(16, 16))
        self._apply_state(False)
        self.toggled.connect(self._apply_state)

    def _apply_state(self, checked: bool):
        self.setObjectName("dangerButton" if checked else "primaryButton")
        # trigger repaint since objectName changed
        self.update()
        # Qt only re-evaluates object-name-based QSS selectors after an
        # explicit unpolish/polish — a plain setObjectName() is invisible
        # until the next full stylesheet reload otherwise.
        self.style().unpolish(self)
        self.style().polish(self)
        icon_name = self._icon_on if checked else self._icon_off
        self.setIcon(get_icon(icon_name, icon_color(self._theme_name, "on-accent")))

    def set_checked_silently(self, checked: bool):
        """
        Syncs the button's visual state to the real backend state without
        re-emitting `toggled` (which would otherwise re-trigger the very
        start/stop action that produced this state change).

        Args:
            checked: True to render the "on" (running/danger) state.

        Returns:
            None.

        Side Effects:
            Mutates the button's checked state, icon, and object name.

        Failure Behavior:
            None.
        """
        self.blockSignals(True)
        self.setChecked(checked)
        self.blockSignals(False)
        self._apply_state(checked)
