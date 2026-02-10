"""
Locale Manager
──────────────
Loads UI strings from JSON files and makes them available to
every widget via a simple ``get(key)`` call.

Adding a new language is as easy as creating a new JSON file.
"""

import json
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal


class LocaleManager(QObject):
    """Manages application translations (i18n)."""

    # Emitted whenever the active locale changes so windows can refresh
    locale_changed = pyqtSignal()

    SUPPORTED_LOCALES: dict[str, str] = {
        "en": "English",
        "es": "Español",
    }

    def __init__(self, locales_dir: str | Path):
        super().__init__()
        self.locales_dir = Path(locales_dir)
        self.current_locale = "en"
        self.strings: dict[str, str] = {}
        self._fallback: dict[str, str] = {}

        # English is always the fallback
        self._load_locale("en")
        self._fallback = dict(self.strings)

    # ── internal ──────────────────────────────────────────────

    def _load_locale(self, code: str):
        locale_file = self.locales_dir / f"{code}.json"
        if locale_file.exists():
            with open(locale_file, "r", encoding="utf-8") as fh:
                self.strings = json.load(fh)
        else:
            self.strings = dict(self._fallback)

    # ── public API ────────────────────────────────────────────

    def set_locale(self, code: str):
        """Switch to *code* (e.g. ``"es"``) and notify listeners."""
        if code not in self.SUPPORTED_LOCALES:
            code = "en"
        self.current_locale = code
        self._load_locale(code)
        self.locale_changed.emit()

    def get(self, key: str, **kwargs) -> str:
        """Return the translated string for *key*.

        Supports ``str.format()`` placeholders::

            locale.get("server_running", port=2121)
        """
        text = self.strings.get(key, self._fallback.get(key, f"[{key}]"))
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError):
                pass
        return text
