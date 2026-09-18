"""
Module: missions.py
───────────────────
Purpose: Interactive networking challenge system with automated real-time verification.

Architectural Role:
Provides guided laboratory exercises inside the CS4S Client. Students are challenged
to trigger specific protocol states (Handshakes, 400 Bad Request syntax errors,
403 Forbidden directory traversal protections, 429 Too Many Requests rate-limiting,
and TLS encryption). The reactive engine monitors socket traffic and validates objectives
instantly.

MintPy Adherence:
- Surface tokens from `src.ui.themes.tokens`.
- Sage/mint accents for educational lab surfaces.
- Icons strictly from MingCute set via `get_icon`.
- 100% localized via `LocaleManager`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.ui.icons.icon_provider import get_icon
from src.ui.themes.tokens import RADIUS, icon_color, mint_gradient, surface_colors
from src.ui.widgets.atoms import MintButton


@dataclass
class MissionData:
    id: str
    title_key: str
    desc_key: str
    hint_key: str
    is_completed: bool = False
    completed_at: str = ""


class MissionsManager(QObject):
    """
    Reactive state machine that verifies student laboratory challenges.

    Signals:
        mission_completed: Emitted when a mission is achieved (mission_id).
        progress_changed: Emitted when progress updates (completed_count, total_count).
        missions_reset: Emitted when progress is cleared.
    """

    mission_completed = pyqtSignal(str)
    progress_changed = pyqtSignal(int, int)
    missions_reset = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._missions: list[MissionData] = [
            MissionData("m1_handshake", "missions.m1_title", "missions.m1_desc", "missions.m1_hint"),
            MissionData("m2_auth", "missions.m2_title", "missions.m2_desc", "missions.m2_hint"),
            MissionData("m3_bad_req", "missions.m3_title", "missions.m3_desc", "missions.m3_hint"),
            MissionData("m4_forbidden", "missions.m4_title", "missions.m4_desc", "missions.m4_hint"),
            MissionData("m5_rate_limit", "missions.m5_title", "missions.m5_desc", "missions.m5_hint"),
            MissionData("m6_tls", "missions.m6_title", "missions.m6_desc", "missions.m6_hint"),
        ]
        self._last_tx: str = ""

    @property
    def missions(self) -> list[MissionData]:
        return self._missions

    def get_mission(self, mission_id: str) -> MissionData | None:
        for m in self._missions:
            if m.id == mission_id:
                return m
        return None

    def get_progress(self) -> tuple[int, int]:
        completed = sum(1 for m in self._missions if m.is_completed)
        return completed, len(self._missions)

    def reset(self) -> None:
        for m in self._missions:
            m.is_completed = False
            m.completed_at = ""
        self._last_tx = ""
        self.missions_reset.emit()
        self.progress_changed.emit(0, len(self._missions))

    def _mark_completed(self, mission_id: str) -> None:
        m = self.get_mission(mission_id)
        if m and not m.is_completed:
            m.is_completed = True
            m.completed_at = datetime.now().strftime("%H:%M:%S")
            self.mission_completed.emit(mission_id)
            comp, tot = self.get_progress()
            self.progress_changed.emit(comp, tot)

    def on_packet_tx(self, packet: str) -> None:
        self._last_tx = packet
        if "HELLO|" in packet or packet.strip() == "HELLO":
            pass

    def on_packet_rx(self, packet: str) -> None:
        # M1: Handshake
        if "220" in packet and ("HELLO" in packet or "CS4S" in packet or "HELLO|" in self._last_tx):
            self._mark_completed("m1_handshake")

        # M2: Auth
        if "230" in packet or "AUTH_OK" in packet:
            self._mark_completed("m2_auth")

        # M3: Bad Request
        if "400" in packet or "BAD_REQUEST" in packet or "BAD_REQ" in packet:
            self._mark_completed("m3_bad_req")

        # M4: Forbidden (Path Traversal defense)
        if "403" in packet or "FORBIDDEN" in packet:
            self._mark_completed("m4_forbidden")

        # M5: Rate Limiting
        if "429" in packet or "TOO_MANY_REQUESTS" in packet or "Rate limit" in packet:
            self._mark_completed("m5_rate_limit")

        # M6: TLS encrypted session
        if "[Encrypted" in packet or "[ENCRYPTED" in packet:
            self._mark_completed("m6_tls")

    def on_tls_connected(self) -> None:
        self._mark_completed("m6_tls")

    def on_auth_success(self) -> None:
        self._mark_completed("m2_auth")


class _MissionCard(QWidget):
    """Visual card for a single lab mission."""

    def __init__(self, mission: MissionData, theme_name: str, locale_func, parent=None):
        super().__init__(parent)
        self.mission = mission
        self._theme_name = theme_name
        self._t = locale_func
        self._build_ui()
        self.update_state()

    def _build_ui(self):
        self.setObjectName("missionCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Header row: Title + Status Badge
        header = QHBoxLayout()
        header.setSpacing(10)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 700;")
        header.addWidget(self.title_label, 1)

        self.badge = QLabel()
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setFixedHeight(24)
        header.addWidget(self.badge)

        layout.addLayout(header)

        # Description
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("font-size: 12px; color: #636E72;")
        layout.addWidget(self.desc_label)

        # Hint box
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("font-size: 11px; font-style: italic; color: #7C9473;")
        layout.addWidget(self.hint_label)

    def update_state(self):
        self.title_label.setText(self._t(self.mission.title_key))
        self.desc_label.setText(self._t(self.mission.desc_key))
        self.hint_label.setText(self._t(self.mission.hint_key))

        colors = surface_colors(self._theme_name)
        if self.mission.is_completed:
            time_txt = f" ({self.mission.completed_at})" if self.mission.completed_at else ""
            self.badge.setText(f"{self._t('missions.completed_badge')}{time_txt}")
            self.badge.setStyleSheet(
                "padding: 2px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; "
                "background-color: #E6F5F2; color: #2F9C86;"
            )
            border_col = "#45B7A0"
        else:
            self.badge.setText(self._t("missions.pending_badge"))
            self.badge.setStyleSheet(
                "padding: 2px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; "
                "background-color: #F1F3F5; color: #8A94A6;"
            )
            border_col = colors["border"]

        bg_col = colors["surface"]
        self.setStyleSheet(
            f"#missionCard {{ background-color: {bg_col}; border: 1px solid {border_col}; "
            f"border-radius: {RADIUS['md']}px; }}"
        )


class LabMissionsWidget(QWidget):
    """
    Complete Guided Missions tab widget for CS4S Lab View.
    """

    def __init__(self, manager: MissionsManager, locale=None, theme_name: str = "mint_light", parent=None):
        super().__init__(parent)
        self.manager = manager
        self.locale = locale
        self._theme_name = theme_name
        self._cards: dict[str, _MissionCard] = {}
        self._build_ui()
        self._wire_signals()
        self.retranslate()

    def _t(self, key: str, **kwargs) -> str:
        if self.locale is None:
            return key
        return self.locale.get(key, **kwargs)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        # ── Top Progress Banner ────────────────────────────────
        top_box = QWidget()
        top_layout = QVBoxLayout(top_box)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        title_row = QHBoxLayout()
        self.title_lbl = QLabel()
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #7C9473;")
        title_row.addWidget(self.title_lbl)
        title_row.addStretch()

        self.reset_btn = MintButton("", self._theme_name)
        self.reset_btn.setIcon(get_icon("refresh", icon_color(self._theme_name)))
        title_row.addWidget(self.reset_btn)
        top_layout.addLayout(title_row)

        self.subtitle_lbl = QLabel()
        self.subtitle_lbl.setStyleSheet("font-size: 12px; color: #636E72;")
        top_layout.addWidget(self.subtitle_lbl)

        # Progress bar
        self.progress_lbl = QLabel()
        self.progress_lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        top_layout.addWidget(self.progress_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.manager.missions))
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        soft, deep = mint_gradient(self._theme_name)
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{ background-color: #E9ECEF; border-radius: 4px; border: none; }}"
            f"QProgressBar::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {soft}, stop:1 {deep}); "
            f"border-radius: 4px; }}"
        )
        top_layout.addWidget(self.progress_bar)

        root.addWidget(top_box)

        # ── Scrollable Missions List ───────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 4, 0, 4)
        list_layout.setSpacing(10)

        for m in self.manager.missions:
            card = _MissionCard(m, self._theme_name, self._t)
            self._cards[m.id] = card
            list_layout.addWidget(card)

        list_layout.addStretch(1)
        scroll.setWidget(list_container)
        root.addWidget(scroll, 1)

    def _wire_signals(self):
        self.manager.mission_completed.connect(self._on_mission_completed)
        self.manager.progress_changed.connect(self._on_progress_changed)
        self.manager.missions_reset.connect(self._on_missions_reset)
        self.reset_btn.clicked.connect(self.manager.reset)

    def _on_mission_completed(self, mission_id: str):
        if mission_id in self._cards:
            self._cards[mission_id].update_state()

    def _on_progress_changed(self, completed: int, total: int):
        self.progress_bar.setValue(completed)
        pct = int((completed / total) * 100) if total > 0 else 0
        self.progress_lbl.setText(self._t("missions.progress", completed=completed, total=total, percent=pct))

    def _on_missions_reset(self):
        for card in self._cards.values():
            card.update_state()

    def retranslate(self):
        self.title_lbl.setText(self._t("missions.title"))
        self.subtitle_lbl.setText(self._t("missions.subtitle"))
        self.reset_btn.setText(self._t("missions.reset_btn"))
        comp, tot = self.manager.get_progress()
        pct = int((comp / tot) * 100) if tot > 0 else 0
        self.progress_lbl.setText(self._t("missions.progress", completed=comp, total=tot, percent=pct))
        for card in self._cards.values():
            card.update_state()
