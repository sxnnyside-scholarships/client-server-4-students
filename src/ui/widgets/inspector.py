"""
Module: inspector.py
────────────────────
Purpose: Displays real-time protocol exchanges and provides a raw network console.

Architectural Role:
Acts as the educational "under the hood" view for the Client application. It receives
signals directly from the `ProtocolHandler` telemetry hooks to visualize exactly what
string bytes are traversing the TCP socket.

Responsibilities:
- Display an auto-scrolling log of `->` (TX) and `<-` (RX) network strings.
- Provide a text input for students to manually inject raw protocol commands.
- Provide educational tooltips explaining the semantics of selected commands.

Expected Collaborators:
- `src.ui.client_window` (hosts this widget in the right-hand splitter panel).
- `src.localization.locale_manager.LocaleManager` (all visible strings).
- `src.ui.icons.icon_provider` (the "Send Raw" action icon).
"""

from datetime import datetime

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor, QTextCharFormat
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.atoms import MintTextInput, MintButton, MintIconButton, MintCheckbox, EmptyStateWidget
from src.ui.icons.icon_provider import get_icon
from src.ui.themes.tokens import console_colors


class ProtocolInspectorWidget(QWidget):
    """
    Real-time visualization and injection of raw protocol data.

    Why it exists:
    A core educational requirement is proving to students that the GUI is just a
    wrapper around text strings. This widget exposes the raw string layer, allowing
    students to bypass the GUI and test the server manually.

    Responsibilities:
    - Rendering timestamped log entries with color-coding (Blue = TX, Green = RX).
    - Emitting `raw_command_requested` signals when the user types a manual command.
    - Parsing user text selections to provide contextual dictionary definitions.

    Non-Responsibilities (Anti-Goals):
    - It does NOT connect directly to the socket (delegated to `ClientBackend`).
    - It does NOT interpret the semantic success or failure of the commands it displays.
    """

    raw_command_requested = pyqtSignal(str)

    # Maps a protocol command to its explanation locale key. The educational
    # copy itself lives in en.json/es.json under these keys (proto_explain_*)
    # so it participates in translation like every other visible string.
    EXPLANATION_KEYS = {
        "HELLO": "inspector.proto_explain_hello",
        "AUTH": "inspector.proto_explain_auth",
        "LIST": "inspector.proto_explain_list",
        "UPLOAD": "inspector.proto_explain_upload",
        "DOWNLOAD": "inspector.proto_explain_download",
        "MKDIR": "inspector.proto_explain_mkdir",
        "DELETE": "inspector.proto_explain_delete",
        "RENAME": "inspector.proto_explain_rename",
        "MOVE": "inspector.proto_explain_move",
        "QUIT": "inspector.proto_explain_quit",
        "PING": "inspector.proto_explain_ping",
        "[ENCRYPTED": "inspector.proto_explain_tls",
    }

    def __init__(self, locale=None, icon_color: str = "#636E72", theme_name: str = "light"):
        super().__init__()
        self.locale = locale
        self._icon_color = icon_color
        self._theme_name = theme_name
        self._log_entries = []
        self._is_paused = False
        self._show_ping = False
        self._build_ui()
        self._wire_signals()
        self.retranslate()

    def _t(self, key: str, **kwargs) -> str:
        """Resolves a locale key, falling back to the key itself when no
        `LocaleManager` was supplied (e.g. standalone widget tests)."""
        if self.locale is None:
            return key
        return self.locale.get(key, **kwargs)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 1. RTT readout — the card's own title (supplied by the enclosing
        # SectionCard) already labels this panel, so this row only carries
        # the one piece of live data that belongs at a glance.
        header_row = QHBoxLayout()
        self.pause_btn = MintIconButton("pause", self._theme_name)
        self.clear_btn = MintIconButton("eraser", self._theme_name)
        self.ping_check = MintCheckbox("", self._theme_name)
        self.ping_check.setChecked(False)

        header_row.addWidget(self.pause_btn)
        header_row.addWidget(self.clear_btn)
        header_row.addWidget(self.ping_check)
        header_row.addStretch()

        self.rtt_label = QLabel()
        self.rtt_label.setObjectName("rttLabel")
        header_row.addWidget(self.rtt_label)

        layout.addLayout(header_row)

        # 2. Console Text Area
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setObjectName("logArea")
        self.empty_state = EmptyStateWidget("", self._theme_name, "leaf")

        self.console.setVisible(False)
        self.empty_state.setVisible(True)

        layout.addWidget(self.console, stretch=1)
        layout.addWidget(self.empty_state, stretch=1)

        # 3. Explanation Panel
        self.explanation_label = QLabel()
        self.explanation_label.setObjectName("explanationLabel")
        self.explanation_label.setWordWrap(True)
        layout.addWidget(self.explanation_label)

        # 4. Raw Input Console
        raw_layout = QHBoxLayout()
        self.raw_input = MintTextInput(self._theme_name)
        self.raw_input.setObjectName("rawCommandInput")

        self.send_btn = MintButton("Send", self._theme_name)
        self.send_btn.setObjectName("secondaryButton")
        self.send_btn.setIcon(get_icon("terminal", self._icon_color))
        self.send_btn.setIconSize(QSize(16, 16))

        raw_layout.addWidget(self.raw_input, stretch=1)
        raw_layout.addWidget(self.send_btn)

        layout.addLayout(raw_layout)

    def _wire_signals(self):
        self.send_btn.clicked.connect(self._on_send_raw)
        self.raw_input.returnPressed.connect(self._on_send_raw)
        self.console.selectionChanged.connect(self._on_selection_changed)
        self.console.cursorPositionChanged.connect(self._on_selection_changed)

        self.pause_btn.clicked.connect(self._on_pause)
        self.clear_btn.clicked.connect(self._on_clear)
        self.ping_check.toggled.connect(self._on_ping_toggled)

    def retranslate(self):
        """
        Applies all locale-dependent copy: header, RTT prefix, hover hint,
        raw-command placeholder/button, and tooltips.

        Args:
            None.

        Returns:
            None.

        Side Effects:
            Mutates widget text and tooltip properties.

        Failure Behavior:
            None.
        """
        self.rtt_label.setText(self._t("inspector.rtt_placeholder"))
        self.explanation_label.setText(self._t("inspector.proto_explain_hint_default"))
        self.raw_input.setPlaceholderText(self._t("inspector.raw_command_placeholder"))
        self.send_btn.setText(self._t("inspector.send_raw_btn"))
        self.send_btn.setToolTip(self._t("tooltip.send_raw"))
        self.raw_input.setToolTip(self._t("tooltip.raw_command_input"))
        self.console.setToolTip(self._t("tooltip.protocol_console"))
        self.pause_btn.setToolTip(self._t("tooltip.inspector_pause"))
        self.clear_btn.setToolTip(self._t("tooltip.inspector_clear"))
        self.ping_check.setText(self._t("tooltip.inspector_show_ping"))
        self.empty_state.set_message(self._t("inspector.empty_console"))

    def set_rtt(self, rtt_ms: float):
        """
        Updates the round-trip latency readout.

        Args:
            rtt_ms: The measured round-trip time in milliseconds.

        Returns:
            None.

        Side Effects:
            Mutates the `rtt_label` text.

        Failure Behavior:
            None.
        """
        self.rtt_label.setText(self._t("inspector.rtt_value", rtt=f"{rtt_ms:.1f}"))

    def log_tx(self, packet: str):
        self._add_log_entry("tx", packet)

    def log_rx(self, packet: str):
        self._add_log_entry("rx", packet)

    def _add_log_entry(self, direction: str, packet: str):
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._log_entries.append((direction, packet, now))
        if len(self._log_entries) > 2000:
            self._log_entries.pop(0)

        if self._is_paused:
            return

        if "PING" in packet or "PONG" in packet:
            if not self._show_ping:
                return

        self._append_to_console(direction, packet, now)
        self._update_empty_state()

    def _append_to_console(self, direction: str, packet: str, timestamp: str):
        colors = console_colors(self._theme_name)
        if direction == "tx":
            color_str = colors["encrypted"] if "[Encrypted" in packet else colors["tx"]
            prefix = "->"
        else:
            color_str = colors["encrypted"] if "[Encrypted" in packet else colors["rx"]
            prefix = "<-"

        color = QColor(color_str)

        scrollbar = self.console.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 4

        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor.insertText(f"[{timestamp}] ", fmt)
        cursor.insertText(f"{prefix} {packet}\n")

        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def _render_logs(self):
        self.console.clear()
        for direction, packet, timestamp in self._log_entries:
            if "PING" in packet or "PONG" in packet:
                if not self._show_ping:
                    continue
            self._append_to_console(direction, packet, timestamp)
        self._update_empty_state()

    def _update_empty_state(self):
        is_empty = self.console.document().isEmpty() or self.console.document().toPlainText().strip() == ""
        self.console.setVisible(not is_empty)
        self.empty_state.setVisible(is_empty)

    def _on_pause(self):
        self._is_paused = not self._is_paused
        if not self._is_paused:
            self._render_logs()

    def _on_clear(self):
        self._log_entries.clear()
        self._render_logs()

    def _on_ping_toggled(self, checked: bool):
        self._show_ping = checked
        self._render_logs()

    def _on_send_raw(self):
        cmd = self.raw_input.text().strip()
        if cmd:
            self.raw_command_requested.emit(cmd)
            self.raw_input.clear()

    def _on_selection_changed(self):
        cursor = self.console.textCursor()

        if cursor.hasSelection():
            text = cursor.selectedText().strip()
        else:
            text = cursor.block().text().strip()
            if text.startswith("["):
                idx = text.find("]")
                if idx != -1:
                    text = text[idx + 1 :].strip()

        if text:
            cmd = text.split("|")[0].upper().replace("->", "").replace("<-", "").strip()
            key = self.EXPLANATION_KEYS.get(cmd)
            if key:
                self.explanation_label.setText(f"{cmd}: {self._t(key)}")
            else:
                self.explanation_label.setText(self._t("inspector.proto_explain_unknown"))
        else:
            self.explanation_label.setText(self._t("inspector.proto_explain_hint_default"))
