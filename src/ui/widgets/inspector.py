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

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor, QTextCharFormat
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.atoms import MintTextInput, MintButton
from src.ui.icons.icon_provider import get_icon


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
        "HELLO": "proto_explain_hello",
        "AUTH": "proto_explain_auth",
        "LIST": "proto_explain_list",
        "UPLOAD": "proto_explain_upload",
        "DOWNLOAD": "proto_explain_download",
        "MKDIR": "proto_explain_mkdir",
        "DELETE": "proto_explain_delete",
        "RENAME": "proto_explain_rename",
        "MOVE": "proto_explain_move",
        "QUIT": "proto_explain_quit",
        "PING": "proto_explain_ping",
    }

    def __init__(self, locale=None, icon_color: str = "#636E72", theme_name: str = "light"):
        super().__init__()
        self.locale = locale
        self._icon_color = icon_color
        self._theme_name = theme_name
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
        header_row.addStretch()

        self.rtt_label = QLabel()
        self.rtt_label.setObjectName("rttLabel")
        header_row.addWidget(self.rtt_label)

        layout.addLayout(header_row)

        # 2. Console Text Area
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setObjectName("logArea")
        layout.addWidget(self.console, stretch=1)

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
        self.rtt_label.setText(self._t("rtt_placeholder"))
        self.explanation_label.setText(self._t("proto_explain_hint_default"))
        self.raw_input.setPlaceholderText(self._t("raw_command_placeholder"))
        self.send_btn.setText(self._t("send_raw_btn"))
        self.send_btn.setToolTip(self._t("tooltip_send_raw"))
        self.raw_input.setToolTip(self._t("tooltip_raw_command_input"))
        self.console.setToolTip(self._t("tooltip_protocol_console"))

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
        self.rtt_label.setText(self._t("rtt_value", rtt=f"{rtt_ms:.1f}"))

    def log_tx(self, packet: str):
        """
        Records an outbound transmission from the client to the server.

        Args:
            packet: The raw string payload (without trailing newlines).

        Returns:
            None.

        Side Effects:
            Mutates the `QTextEdit` buffer. Auto-scrolls to the bottom.
            Text is styled in Blue.

        Failure Behavior:
            None.
        """
        self._log(f"-> {packet}", QColor("#0000AA"))

    def log_rx(self, packet: str):
        """
        Records an inbound transmission from the server to the client.

        Args:
            packet: The raw string payload (without trailing newlines).

        Returns:
            None.

        Side Effects:
            Mutates the `QTextEdit` buffer. Auto-scrolls to the bottom.
            Text is styled in Green.

        Failure Behavior:
            None.
        """
        self._log(f"<- {packet}", QColor("#008800"))

    def _log(self, text: str, color: QColor):
        """
        Internal helper to append formatted text to the console.

        Args:
            text: The string to append.
            color: The `QColor` format to apply to the timestamp.

        Returns:
            None.

        Side Effects:
            Mutates the `QTextEdit` buffer.
            Forces the widget to scroll to the absolute bottom.

        Failure Behavior:
            None.
        """
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Move cursor to end
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Apply color format
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor.insertText(f"[{now}] ", fmt)

        # The actual packet
        cursor.insertText(f"{text}\n")

        # Auto-scroll
        self.console.ensureCursorVisible()

    def _on_send_raw(self):
        cmd = self.raw_input.text().strip()
        if cmd:
            self.raw_command_requested.emit(cmd)
            self.raw_input.clear()

    def _on_selection_changed(self):
        """
        Triggered by Qt when the user highlights text in the console.
        Updates the explanation label if the selected text matches a known command.

        Args:
            None.

        Returns:
            None.

        Side Effects:
            Mutates the `explanation_label` text.

        Failure Behavior:
            If the highlighted text is not a valid command, displays a fallback message.
        """
        cursor = self.console.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText().strip()
            # Try to match the first word with a known command
            cmd = text.split("|")[0].upper().replace("->", "").replace("<-", "").strip()
            key = self.EXPLANATION_KEYS.get(cmd)
            if key:
                self.explanation_label.setText(f"{cmd}: {self._t(key)}")
            else:
                self.explanation_label.setText(self._t("proto_explain_unknown"))
        else:
            self.explanation_label.setText(self._t("proto_explain_hint_default"))
