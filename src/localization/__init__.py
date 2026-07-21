"""
Package: src.localization
─────────────────────────
Purpose: Provides multi-language support (i18n) and string management for the application's graphical user interfaces.

Architectural Role:
Acts as a centralized string repository. Instead of hardcoding English text into UI widgets,
all visible text is fetched dynamically through this package, allowing the application to
swap languages at runtime.

Responsibilities:
- Load JSON translation files (`en.json`, `es.json`, etc.).
- Provide a unified string retrieval API with formatting support.
- Broadcast Qt signals when the active language changes so the UI can redraw itself.

Public API:
- `locale_manager.LocaleManager`: The core singleton-style manager that holds translation dictionaries and emits signals on change.

Expected Collaborators:
- `src.ui`: All visual windows and widgets consume `LocaleManager.get()` to render text.
- `src.core.config`: Stores and retrieves the user's preferred language string to persist across reboots.
"""
