"""
Module: locale_manager.py
─────────────────────────
Purpose: Loads UI strings from JSON files and manages application translations (i18n).

Architectural Role:
Acts as the central string provider for the Presentation Layer. It decouples 
display strings from the UI code, allowing the application to switch languages dynamically.

Responsibilities:
- Parse `.json` localization files into memory.
- Provide a unified string retrieval interface with interpolation support.
- Emit Qt signals when the language changes so UI widgets can trigger a redraw.

Expected Collaborators:
- `src.ui.launcher`, `src.ui.client_window`, `src.ui.server_window` (all UI files)
- `src.core.config` (to read the initial language preference)
"""

import json
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal


class LocaleManager(QObject):
    """
    Manages application translations and string interpolation.

    Why it exists:
    Provides a reactive, singleton-like mechanism for widgets to fetch text. By using 
    a centralized manager that emits a `locale_changed` signal, the entire UI can 
    translate itself instantly without requiring a full application restart.

    Responsibilities:
    - Managing in-memory dictionaries of the active locale and the fallback locale (English).
    - Emitting `locale_changed` signals across the Qt event loop.

    Non-Responsibilities (Anti-Goals):
    - It does NOT mutate or redraw UI widgets directly. It simply broadcasts the event.
    - It does NOT persist the user's language choice to disk (delegated to `ConfigManager`).
    """

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
        """
        Switches the active language and notifies all listening UI widgets.

        Args:
            code: The language code (e.g., "en", "es").

        Returns:
            None.

        Side Effects:
            Mutates the internal `self.strings` dictionary by reading from disk.
            Emits the `locale_changed` PyQt signal.

        Failure Behavior:
            If the requested `code` is not supported, it silently falls back to "en".
            If the JSON file is missing, it falls back to the in-memory English dictionary.
        """
        if code not in self.SUPPORTED_LOCALES:
            code = "en"
        self.current_locale = code
        self._load_locale(code)
        self.locale_changed.emit()

    def get(self, key: str, **kwargs) -> str:
        """
        Retrieves the translated string for a given key, optionally formatting it.

        Args:
            key: The string identifier defined in the locale JSON files.
            **kwargs: Arbitrary keyword arguments used for `str.format()` interpolation.

        Returns:
            The translated string, or a fallback string if the key is missing.

        Side Effects:
            None. Reads from the in-memory dictionary.

        Failure Behavior:
            Returns the English fallback string if the key is missing in the active locale.
            Returns `[key]` if the key is missing even in the fallback dictionary.
            Swallows `KeyError` or `IndexError` if string interpolation variables do not match.
        """
        text = self.strings.get(key, self._fallback.get(key, f"[{key}]"))
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError):
                pass
        return text
