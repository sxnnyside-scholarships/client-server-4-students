"""
Common Widgets & Helpers
────────────────────────
Small reusable pieces shared across the Launcher, Client, and Server UIs.
"""

import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


SXNNYSIDE_URL = "https://www.sxnnysideproject.com"


def format_file_size(size_bytes: int) -> str:
    """Return a human-friendly file-size string.

    >>> format_file_size(1023)
    '1023 B'
    >>> format_file_size(10240)
    '10.0 KB'
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    return f"{size_bytes / (1024 ** 3):.1f} GB"


class BrandingFooter(QLabel):
    """A subtle branding footer displayed at the bottom of every window.

    Shows the text provided by the locale system, with "Sxnnyside Project"
    rendered as a clickable hyperlink that opens in the default browser.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("brandingFooter")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setOpenExternalLinks(False)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.linkActivated.connect(self._open_link)
        self.setStyleSheet(
            "QLabel#brandingFooter {"
            "  color: #888888;"
            "  font-size: 11px;"
            "  padding: 4px 0;"
            "}"
        )
        # Default text (overwritten by retranslate calls)
        self._set_text("Developed by Sxnnyside Scholarships", "Sxnnyside Project")

    def _set_text(self, prefix: str, link_text: str):
        """Build the HTML label: prefix · <a>link_text</a>."""
        self.setText(
            f'{prefix} · <a href="{SXNNYSIDE_URL}" '
            f'style="color:#888888; text-decoration:none;">{link_text}</a>'
        )

    def update_text(self, prefix: str, link_text: str):
        """Public API used by ``retranslate()`` in each window."""
        self._set_text(prefix, link_text)

    @staticmethod
    def _open_link(url: str):
        webbrowser.open(url)


class LabeledInput(QWidget):
    """A horizontal ``QLabel + QLineEdit`` pair."""

    def __init__(self, label_text: str = "", placeholder: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = QLabel(label_text)
        self.label.setMinimumWidth(60)
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)

        layout.addWidget(self.label)
        layout.addWidget(self.input)

    def text(self) -> str:
        return self.input.text().strip()

    def set_text(self, value: str):
        self.input.setText(value)
