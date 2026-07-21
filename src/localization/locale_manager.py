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

import i18n
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal


class LocaleManager(QObject):
    """
    Wraps python-i18n to provide dynamic translation retrieval while adhering
    to the Qt Event Loop via QObject signals.

    Why this class exists:
    While `python-i18n` handles dictionary lookups, it is unaware of the GUI.
    This class bridges the gap by wrapping the library and emitting a PyQt signal
    whenever the language changes, notifying all active UI components to retranslate themselves.

    What it owns:
    - Initializing the `python-i18n` library.
    - Providing type-safe and fallback-aware string lookups via `get()`.

    What it deliberately does not own:
    - Retranslating the UI directly (widgets must connect to `locale_changed` and update themselves).

    ## Educational Note
    GUI frameworks like PyQt are strictly single-threaded. By inheriting from `QObject`
    and using `pyqtSignal()`, this class ensures that any language-change request safely
    propagates to the main thread's event queue. Without this signal-slot architecture,
    changing the language dynamically across deeply nested widget trees would require
    manual, fragile callbacks.
    """

    locale_changed = pyqtSignal()

    SUPPORTED_LOCALES: dict[str, str] = {
        "en": "English",
        "es": "Español",
    }

    def __init__(self, locales_dir: str | Path):
        super().__init__()
        # Register this instance as the process-wide locale provider so leaf
        # components without an injected LocaleManager (e.g. `MintDialog`
        # classmethod helpers) can still resolve their own chrome strings.
        global _global_locale
        _global_locale = self
        self.locales_dir = str(locales_dir)
        self.current_locale = "en"

        i18n.load_path.append(self.locales_dir)
        i18n.set("file_format", "json")
        i18n.set("filename_format", "{locale}.{format}")
        i18n.set("fallback", "en")
        i18n.set("skip_locale_root_data", True)

        self.set_locale("en")

    def set_locale(self, code: str):
        """
        Switches the application's current language and notifies observers.

        Purpose:
            Update the underlying `python-i18n` active locale and broadcast the
            change to the UI layer.

        Inputs:
            code (str): The two-letter language code (e.g., 'en', 'es').

        Side effects:
            - Modifies the global `i18n.locale` state.
            - Emits the `locale_changed` signal on the Qt event loop.

        Failure behavior:
            Falls back to 'en' if an unsupported locale code is provided.
        """
        if code not in self.SUPPORTED_LOCALES:
            code = "en"
        self.current_locale = code
        i18n.set("locale", code)
        self.locale_changed.emit()

    def get(self, key: str, **kwargs) -> str:
        """
        Retrieves a translated string from the loaded JSON dictionaries.

        Purpose:
            Provides a safe wrapper around `i18n.t` to handle missing keys gracefully.

        Inputs:
            key (str): The namespace key (e.g., 'client.upload_success').
            kwargs: Optional format variables for string interpolation.

        Outputs:
            str: The translated string.

        Failure behavior:
            If the key is not found in the current or fallback language files,
            it returns the literal key wrapped in brackets (e.g., '[client.invalid]').
        """
        # python-i18n sets the namespace to the filename prefix if no namespace is in the filename_format.
        # Since our format is `{locale}.{format}`, the file `en.json` uses `en` as the namespace.
        namespaced_key = f"{self.current_locale}.{key}"
        text = i18n.t(namespaced_key, **kwargs)

        # i18n returns the key if translation is missing
        if text == namespaced_key:
            if self.current_locale != "en":
                fallback_key = f"en.{key}"
                fallback_text = i18n.t(fallback_key, **kwargs)
                if fallback_text != fallback_key:
                    return fallback_text
            return f"[{key}]"

        return text


# The most recently constructed LocaleManager. CS4S creates exactly one at
# bootstrap (in main.py), so this is a simple service-locator for widgets
# that are instantiated without dependency injection.
_global_locale: LocaleManager | None = None
