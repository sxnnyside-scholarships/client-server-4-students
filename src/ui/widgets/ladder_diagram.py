"""
Module: ladder_diagram.py
─────────────────────────
Purpose: Interactive Ladder Sequence Diagram (temporal packet flow visualization).

Architectural Role:
Renders a chronological sequence diagram of network interactions between Client and Server.
Features two vertical lifelines with directed arrows showing protocol requests, responses,
status codes, exact timestamps, and calculated latency (RTT / delta).

MintPy Adherence:
- Surface tokens, typography scale, and atomic controls.
- Mint/sage botanical palette for success states; red for protocol errors (4xx/5xx).
- 100% localized via `LocaleManager`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.ui.themes.tokens import get_monospace_font, surface_colors
from src.ui.widgets.atoms import EmptyStateWidget, MintCheckbox, MintIconButton


@dataclass
class SequenceMessage:
    direction: str  # "tx" or "rx"
    packet_text: str
    timestamp: str
    epoch_time: float
    status_code: int | None = None
    delta_ms: float | None = None
    is_encrypted: bool = False


class _LadderCanvas(QWidget):
    """Custom-painted canvas rendering the vertical lifelines and message arrows."""

    ROW_HEIGHT = 44
    HEADER_OFFSET = 30
    LIFELINE_INSET = 140

    def __init__(self, theme_name: str, parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self._messages: list[SequenceMessage] = []
        self._hide_ping: bool = False
        self.setMouseTracking(True)

    def set_messages(self, messages: list[SequenceMessage], hide_ping: bool):
        self._messages = messages
        self._hide_ping = hide_ping
        self._update_geometry()
        self.update()

    def _filtered_messages(self) -> list[SequenceMessage]:
        if not self._hide_ping:
            return self._messages
        return [m for m in self._messages if "PING" not in m.packet_text and "PONG" not in m.packet_text]

    def _update_geometry(self):
        count = len(self._filtered_messages())
        total_height = self.HEADER_OFFSET + (count * self.ROW_HEIGHT) + 40
        self.setMinimumHeight(max(300, total_height))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        colors = surface_colors(self._theme_name)
        w = self.width()
        h = self.height()

        x_client = float(self.LIFELINE_INSET)
        x_server = float(w - self.LIFELINE_INSET)

        # ── Draw Vertical Lifelines ─────────────────────────────
        line_pen = QPen(QColor(colors["border"]), 2, Qt.PenStyle.DashLine)
        painter.setPen(line_pen)
        painter.drawLine(QPointF(x_client, self.HEADER_OFFSET), QPointF(x_client, h - 20))
        painter.drawLine(QPointF(x_server, self.HEADER_OFFSET), QPointF(x_server, h - 20))

        # ── Draw Message Arrows ─────────────────────────────────
        messages = self._filtered_messages()
        font = QFont("Inter", 9)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)

        y = float(self.HEADER_OFFSET + 20)

        for msg in messages:
            is_tx = msg.direction == "tx"
            is_err = msg.status_code is not None and msg.status_code >= 400

            if is_err:
                arrow_color = QColor("#D63031")  # Status error
            elif msg.is_encrypted:
                arrow_color = QColor("#7C9473")  # Sage encryption
            elif is_tx:
                arrow_color = QColor("#45B7A0")  # Mint primary
            else:
                arrow_color = QColor("#2F9C86")  # Mint response

            pen = QPen(arrow_color, 2)
            painter.setPen(pen)
            painter.setBrush(arrow_color)

            # Arrow geometry
            if is_tx:
                # Client -> Server (left to right)
                x_start = x_client
                x_end = x_server
                painter.drawLine(QPointF(x_start, y), QPointF(x_end, y))

                # Arrowhead pointing right
                head = QPolygonF(
                    [
                        QPointF(x_end, y),
                        QPointF(x_end - 8, y - 4),
                        QPointF(x_end - 8, y + 4),
                    ]
                )
                painter.drawPolygon(head)

                # Text label centered above arrow
                label_rect = QRectF(x_start + 10, y - 18, x_end - x_start - 20, 16)
                painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, msg.packet_text[:40])

                # Timestamp label on the left margin
                time_font = get_monospace_font(8)
                painter.setFont(time_font)
                painter.setPen(QColor(colors["text_muted"]))
                painter.drawText(
                    QRectF(10, y - 8, x_client - 15, 16),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    msg.timestamp,
                )
                painter.setFont(font)

            else:
                # Server -> Client (right to left)
                x_start = x_server
                x_end = x_client
                painter.drawLine(QPointF(x_start, y), QPointF(x_end, y))

                # Arrowhead pointing left
                head = QPolygonF(
                    [
                        QPointF(x_end, y),
                        QPointF(x_end + 8, y - 4),
                        QPointF(x_end + 8, y + 4),
                    ]
                )
                painter.drawPolygon(head)

                # Text label centered above arrow
                label_rect = QRectF(x_end + 10, y - 18, x_start - x_end - 20, 16)
                painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, msg.packet_text[:40])

                # Timestamp and delta on the right margin
                time_font = get_monospace_font(8)
                painter.setFont(time_font)
                painter.setPen(QColor(colors["text_muted"]))
                right_text = msg.timestamp
                if msg.delta_ms is not None:
                    right_text += f" (Δ {msg.delta_ms:.1f}ms)"
                painter.drawText(
                    QRectF(x_server + 15, y - 8, w - x_server - 20, 16),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    right_text,
                )
                painter.setFont(font)

            y += self.ROW_HEIGHT

        painter.end()


class LadderDiagramWidget(QWidget):
    """
    Complete interactive Sequence Diagram widget with controls and lifeline headers.
    """

    def __init__(self, locale=None, theme_name: str = "mint_light", parent=None):
        super().__init__(parent)
        self.locale = locale
        self._theme_name = theme_name
        self._messages: list[SequenceMessage] = []
        self._last_tx_time: float | None = None
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
        root.setSpacing(10)

        # ── Toolbar Row ─────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.clear_btn = MintIconButton("eraser", self._theme_name)
        self.ping_check = MintCheckbox("", self._theme_name)
        self.ping_check.setChecked(False)

        toolbar.addWidget(self.clear_btn)
        toolbar.addWidget(self.ping_check)
        toolbar.addStretch()

        self.rtt_label = QLabel()
        self.rtt_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #45B7A0;")
        toolbar.addWidget(self.rtt_label)

        root.addLayout(toolbar)

        # ── Lifeline Column Headers ─────────────────────────────
        lifelines_box = QHBoxLayout()
        lifelines_box.setContentsMargins(10, 0, 10, 0)

        self.client_badge = QLabel()
        self.client_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.client_badge.setFixedHeight(28)
        self.client_badge.setStyleSheet(
            "padding: 4px 16px; border-radius: 8px; font-size: 12px; font-weight: 700; "
            "background-color: #E6F5F2; color: #2F9C86; border: 1px solid #45B7A0;"
        )
        lifelines_box.addWidget(self.client_badge)

        lifelines_box.addStretch()

        self.server_badge = QLabel()
        self.server_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.server_badge.setFixedHeight(28)
        self.server_badge.setStyleSheet(
            "padding: 4px 16px; border-radius: 8px; font-size: 12px; font-weight: 700; "
            "background-color: #F0F4EF; color: #7C9473; border: 1px solid #7C9473;"
        )
        lifelines_box.addWidget(self.server_badge)

        root.addLayout(lifelines_box)

        # ── Scroll Area with Canvas / Empty State ───────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self.canvas = _LadderCanvas(self._theme_name)
        self.empty_state = EmptyStateWidget("", self._theme_name, "leaf")

        self.scroll.setWidget(self.canvas)
        root.addWidget(self.scroll, 1)
        root.addWidget(self.empty_state, 1)

        self._update_visibility()

    def _wire_signals(self):
        self.clear_btn.clicked.connect(self.clear)
        self.ping_check.toggled.connect(self._on_ping_toggled)

    def add_tx(self, packet: str):
        now = datetime.now()
        ts_str = now.strftime("%H:%M:%S.%f")[:-3]
        epoch = now.timestamp()
        self._last_tx_time = epoch
        is_enc = "[Encrypted" in packet or "[ENCRYPTED" in packet

        msg = SequenceMessage(
            direction="tx",
            packet_text=packet.strip(),
            timestamp=ts_str,
            epoch_time=epoch,
            is_encrypted=is_enc,
        )
        self._messages.append(msg)
        self._refresh()

    def add_rx(self, packet: str):
        now = datetime.now()
        ts_str = now.strftime("%H:%M:%S.%f")[:-3]
        epoch = now.timestamp()

        delta = None
        if self._last_tx_time is not None:
            delta = (epoch - self._last_tx_time) * 1000.0

        # Detect status code
        status_code = None
        parts = packet.strip().split()
        if parts and parts[0].isdigit():
            status_code = int(parts[0])

        is_enc = "[Encrypted" in packet or "[ENCRYPTED" in packet

        msg = SequenceMessage(
            direction="rx",
            packet_text=packet.strip(),
            timestamp=ts_str,
            epoch_time=epoch,
            status_code=status_code,
            delta_ms=delta,
            is_encrypted=is_enc,
        )
        self._messages.append(msg)
        self._refresh()

    def set_rtt(self, rtt_ms: float):
        self.rtt_label.setText(self._t("ladder.rtt_badge", ms=f"{rtt_ms:.1f}"))

    def clear(self):
        self._messages.clear()
        self._last_tx_time = None
        self._refresh()

    def _on_ping_toggled(self, checked: bool):
        self._refresh()

    def _refresh(self):
        self.canvas.set_messages(self._messages, self.ping_check.isChecked())
        self._update_visibility()
        # Auto-scroll to bottom
        scrollbar = self.scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _update_visibility(self):
        has_items = bool(self.canvas._filtered_messages())
        self.scroll.setVisible(has_items)
        self.empty_state.setVisible(not has_items)

    def retranslate(self):
        self.clear_btn.setToolTip(self._t("ladder.clear"))
        self.ping_check.setText(self._t("ladder.hide_ping"))
        self.client_badge.setText(self._t("ladder.client_lifeline"))
        self.server_badge.setText(self._t("ladder.server_lifeline"))
        self.empty_state.set_message(self._t("ladder.empty"))
        self.rtt_label.setText(self._t("ladder.rtt_badge", ms="--"))
