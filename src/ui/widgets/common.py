"""
Common Widgets & Helpers
────────────────────────
Small reusable pieces shared across the Launcher, Client, and Server UIs.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


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
