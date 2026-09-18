"""
Module: udp_comparison.py
─────────────────────────
Purpose: Educational UI widget comparing TCP stream delivery against UDP datagram transmission.

Architectural Role:
Integrated into the Client Lab View stack as a dedicated tab. Provides students
with an interactive testbench to generate datagram bursts, observe connectionless
packet loss and latency, and visually compare UDP against reliable TCP stream delivery.

Responsibilities:
- Provide configurable burst parameters (packet count, payload size).
- Asynchronously transmit datagram bursts using `UDPProbeClient`.
- Render side-by-side metric comparison cards (TCP Reliable vs UDP Best-effort).
- Render an interactive visual packet matrix (showing each individual datagram's fate).
- Comply with MintPy design tokens (typography, sage/mint palette, atomic controls).
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.localization.locale_manager import LocaleManager
from src.network.client.udp_client import UDPProbeClient
from src.ui.icons.icon_provider import get_icon
from src.ui.themes.tokens import (
    accent_color,
    icon_color,
    status_color,
    surface_colors,
    text_color,
)
from src.ui.widgets.atoms import MintButton


class _CardWidget(QFrame):
    """Custom-styled container frame matching MintPy surface tokens."""

    def __init__(self, theme_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.set_theme(theme_name)

    def set_theme(self, theme_name: str, custom_border: str | None = None):
        surfaces = surface_colors(theme_name)
        border = custom_border or surfaces.get("border", "#DFE6E9")
        bg = surfaces.get("surface", "#ffffff")
        self.setStyleSheet(
            f"""
            QFrame#cardFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            """
        )


class _PacketChip(QWidget):
    """Visual representation of a single datagram in a burst."""

    def __init__(self, seq: int, received: bool, rtt_ms: float, theme_name: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        seq_lbl = QLabel(f"#{seq}")
        seq_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        seq_lbl.setStyleSheet("font-size: 11px; font-weight: bold;")

        stat_lbl = QLabel(f"{rtt_ms:.1f}ms" if received else "LOST")
        stat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stat_lbl.setStyleSheet("font-size: 10px;")

        layout.addWidget(seq_lbl)
        layout.addWidget(stat_lbl)

        surfaces = surface_colors(theme_name)
        bg = surfaces.get("surface", "#ffffff")
        if received:
            accent = status_color(theme_name, "online")
            border = f"1px solid {accent}"
            text_c = accent
        else:
            accent = status_color(theme_name, "error")
            border = f"1px dashed {accent}"
            text_c = accent

        stat_lbl.setStyleSheet(f"font-size: 10px; color: {text_c}; font-weight: 600;")
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {bg};
                border: {border};
                border-radius: 6px;
            }}
            """
        )
        self.setFixedSize(54, 42)


class UDPComparisonWidget(QWidget):
    """
    Lab View widget comparing connection-oriented TCP vs connectionless UDP.
    """

    burst_finished = pyqtSignal(dict)

    def __init__(
        self,
        locale: LocaleManager,
        theme_name: str,
        host: str = "127.0.0.1",
        udp_port: int = 2122,
        parent=None,
    ):
        super().__init__(parent)
        self.locale = locale
        self._theme_name = theme_name
        self.host = host
        self.udp_port = udp_port

        self._probe_client = UDPProbeClient()
        self._is_transmitting = False

        self.burst_finished.connect(self._on_burst_completed)
        self._build_ui()
        self.retranslate()

    def set_target(self, host: str, udp_port: int):
        """Updates the destination host and UDP port."""
        self.host = host
        self.udp_port = udp_port

    def set_theme(self, theme_name: str):
        """Updates theme tokens."""
        self._theme_name = theme_name
        self._apply_theme()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        # ── Header ───────────────────────────────────────────
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        header_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setStyleSheet("font-size: 12px;")
        header_layout.addWidget(self.subtitle_label)

        root.addLayout(header_layout)

        # ── Controls Bar ─────────────────────────────────────
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        self.count_label = QLabel()
        controls_layout.addWidget(self.count_label)

        self.count_combo = QComboBox()
        self.count_combo.addItems(["10", "25", "50", "100"])
        self.count_combo.setCurrentText("25")
        controls_layout.addWidget(self.count_combo)

        self.size_label = QLabel()
        controls_layout.addWidget(self.size_label)

        self.size_combo = QComboBox()
        self.size_combo.addItems(["64 B", "256 B", "512 B", "1024 B"])
        self.size_combo.setCurrentText("256 B")
        controls_layout.addWidget(self.size_combo)

        self.burst_btn = MintButton("", self._theme_name)
        self.burst_btn.setIcon(get_icon("play", icon_color(self._theme_name, "on-accent")))
        self.burst_btn.clicked.connect(self._start_burst)
        controls_layout.addWidget(self.burst_btn)

        controls_layout.addStretch()
        root.addLayout(controls_layout)

        # ── Side-by-Side Comparison Cards ────────────────────
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        # TCP Card
        self.tcp_card = _CardWidget(self._theme_name)
        tcp_layout = QVBoxLayout(self.tcp_card)
        tcp_layout.setContentsMargins(14, 14, 14, 14)
        tcp_layout.setSpacing(6)

        self.tcp_header = QLabel()
        self.tcp_header.setStyleSheet("font-size: 14px; font-weight: 700;")
        tcp_layout.addWidget(self.tcp_header)

        self.tcp_prop1 = QLabel("Mode: Connection-Oriented Stream")
        self.tcp_prop2 = QLabel("Reliability: 100% Guaranteed (Auto ACK/Retransmit)")
        self.tcp_prop3 = QLabel("Ordering: Strictly In-Order Stream")
        self.tcp_prop4 = QLabel("Loss Rate: 0.0% (Packets retransmitted)")
        self.tcp_prop5 = QLabel("Overhead: 3-Way Handshake + 20B Header + ACKs")

        for lbl in (self.tcp_prop1, self.tcp_prop2, self.tcp_prop3, self.tcp_prop4, self.tcp_prop5):
            lbl.setStyleSheet("font-size: 11px;")
            tcp_layout.addWidget(lbl)
        tcp_layout.addStretch()

        cards_layout.addWidget(self.tcp_card, 1)

        # UDP Card
        self.udp_card = _CardWidget(self._theme_name)
        udp_layout = QVBoxLayout(self.udp_card)
        udp_layout.setContentsMargins(14, 14, 14, 14)
        udp_layout.setSpacing(6)

        self.udp_header = QLabel()
        self.udp_header.setStyleSheet("font-size: 14px; font-weight: 700;")
        udp_layout.addWidget(self.udp_header)

        self.udp_prop1 = QLabel("Mode: Connectionless Datagrams")
        self.udp_prop2 = QLabel("Reliability: Best-Effort (No transport ACKs)")
        self.udp_prop3 = QLabel("Ordering: Unordered / Out-of-Order")
        self.udp_metrics_loss = QLabel("Loss Rate: --")
        self.udp_metrics_latency = QLabel("Avg Latency: --")
        self.udp_metrics_throughput = QLabel("Throughput: --")

        for lbl in (
            self.udp_prop1,
            self.udp_prop2,
            self.udp_prop3,
            self.udp_metrics_loss,
            self.udp_metrics_latency,
            self.udp_metrics_throughput,
        ):
            lbl.setStyleSheet("font-size: 11px;")
            udp_layout.addWidget(lbl)
        udp_layout.addStretch()

        cards_layout.addWidget(self.udp_card, 1)
        root.addLayout(cards_layout)

        # ── Visual Datagram Matrix ───────────────────────────
        self.matrix_card = _CardWidget(self._theme_name)
        matrix_box = QVBoxLayout(self.matrix_card)
        matrix_box.setContentsMargins(12, 10, 12, 10)
        matrix_box.setSpacing(6)

        self.matrix_title = QLabel("Datagram Burst Stream (Sequence & Round-Trip)")
        self.matrix_title.setStyleSheet("font-size: 12px; font-weight: 700;")
        matrix_box.addWidget(self.matrix_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(130)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.matrix_container = QWidget()
        self.matrix_grid = QGridLayout(self.matrix_container)
        self.matrix_grid.setContentsMargins(4, 4, 4, 4)
        self.matrix_grid.setSpacing(6)
        scroll.setWidget(self.matrix_container)

        matrix_box.addWidget(scroll)
        root.addWidget(self.matrix_card)

        # ── Status Bar ───────────────────────────────────────
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 11px;")
        root.addWidget(self.status_label)

        # ── Educational Insight Note ─────────────────────────
        self.concept_card = _CardWidget(self._theme_name)
        concept_layout = QVBoxLayout(self.concept_card)
        concept_layout.setContentsMargins(12, 10, 12, 10)

        self.concept_label = QLabel()
        self.concept_label.setWordWrap(True)
        self.concept_label.setStyleSheet("font-size: 11px; line-height: 1.4;")
        concept_layout.addWidget(self.concept_label)

        root.addWidget(self.concept_card)
        self._apply_theme()

    def _apply_theme(self):
        theme = self._theme_name
        muted = text_color(theme, "muted")
        pri = text_color(theme, "primary")
        surfaces = surface_colors(theme)
        border = surfaces.get("border", "#DFE6E9")
        accent = accent_color(theme)

        self.title_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {pri};")
        self.subtitle_label.setStyleSheet(f"font-size: 12px; color: {muted};")
        self.count_label.setStyleSheet(f"font-size: 12px; color: {pri};")
        self.size_label.setStyleSheet(f"font-size: 12px; color: {pri};")
        self.status_label.setStyleSheet(f"font-size: 11px; color: {muted};")

        combo_style = f"""
            QComboBox {{
                border: 1px solid {border};
                border-radius: 6px;
                padding: 4px 8px;
                background-color: {surfaces.get("surface", "#ffffff")};
                color: {pri};
                min-width: 70px;
            }}
        """
        self.count_combo.setStyleSheet(combo_style)
        self.size_combo.setStyleSheet(combo_style)

        self.tcp_card.set_theme(theme)
        self.udp_card.set_theme(theme)
        self.matrix_card.set_theme(theme)
        self.concept_card.set_theme(theme, custom_border=accent)
        self.concept_label.setStyleSheet(f"font-size: 11px; color: {pri};")

    def retranslate(self):
        """Refreshes all localized labels."""
        t = self.locale.get
        self.title_label.setText(t("udp.title"))
        self.subtitle_label.setText(t("udp.subtitle"))
        self.burst_btn.setText(t("udp.burst_btn"))
        self.count_label.setText(t("udp.datagrams_count"))
        self.size_label.setText(t("udp.packet_size"))
        self.tcp_header.setText(t("udp.metrics_tcp"))
        self.udp_header.setText(t("udp.metrics_udp"))
        self.concept_label.setText(t("udp.concept_note"))

        if not self._is_transmitting:
            self.status_label.setText(t("udp.status_idle"))

    def _start_burst(self):
        if self._is_transmitting:
            return

        try:
            count = int(self.count_combo.currentText())
        except ValueError:
            count = 25

        size_str = self.size_combo.currentText().split()[0]
        try:
            size = int(size_str)
        except ValueError:
            size = 256

        self._is_transmitting = True
        self.burst_btn.setEnabled(False)

        t = self.locale.get
        self.status_label.setText(t("udp.status_transmitting", count=count, host=self.host, port=self.udp_port))

        # Clear existing packet chips
        while self.matrix_grid.count():
            item = self.matrix_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        def _on_done(res: dict):
            self.burst_finished.emit(res)

        self._probe_client.transmit_burst_async(
            host=self.host,
            port=self.udp_port,
            count=count,
            packet_size=size,
            on_completed=_on_done,
        )

    def _on_burst_completed(self, results: dict):
        self._is_transmitting = False
        self.burst_btn.setEnabled(True)

        try:
            received = results.get("total_received", 0)
            total = results.get("total_sent", 0)
            loss_pct = results.get("loss_rate_pct", 0.0)
            avg_rtt = results.get("avg_rtt_ms", 0.0)
            throughput = results.get("throughput_kbps", 0.0)

            t = self.locale.get
            self.status_label.setText(
                t(
                    "udp.status_completed",
                    received=received,
                    total=total,
                    loss=f"{loss_pct:.1f}",
                    latency=f"{avg_rtt:.1f}",
                )
            )

            # Update UDP metrics
            self.udp_metrics_loss.setText(f"{t('udp.loss_rate')} {loss_pct:.1f}% ({total - received} lost)")
            self.udp_metrics_latency.setText(f"{t('udp.avg_latency')} {avg_rtt:.2f} ms")
            self.udp_metrics_throughput.setText(f"{t('udp.throughput')} {throughput:.1f} KB/s")

            # Render packet chips in matrix
            packets = results.get("packets", [])
            cols = 10
            for i, pkt in enumerate(packets):
                row = i // cols
                col = i % cols
                chip = _PacketChip(
                    seq=pkt["seq"],
                    received=pkt["received"],
                    rtt_ms=pkt["rtt_ms"],
                    theme_name=self._theme_name,
                )
                self.matrix_grid.addWidget(chip, row, col)

        except (RuntimeError, AttributeError):
            pass
