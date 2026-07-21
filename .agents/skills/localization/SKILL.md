---
name: localization
description: Rules for localizing UI strings and managing i18n
---

# Localization Guidelines

This repository uses `python-i18n` for internationalization. Follow these guidelines whenever you add, modify, or review user-facing strings.

## 1. No Hardcoded Strings
- Never write hardcoded UI strings in Python or QML files. 
- Example: Do not use `button.setText("Start")`. Instead, use `button.setText(locale.get("launcher.start_btn"))`.
- This applies to tooltips, dialogs, labels, window titles, and any text rendered on the screen.

## 2. The `LocaleManager` Wrapper
- `LocaleManager` (in `src/localization/locale_manager.py`) wraps `python-i18n` to preserve the `locale_changed` PyQt6 signal.
- Always use `LocaleManager.get(key, **kwargs)` to fetch strings inside UI components. Do not import `i18n` directly into UI files.

## 3. Namespace Formatting
- JSON keys must use the `namespace.key` structure. We rely on the `skip_locale_root_data=True` config which flattens the JSON files.
- The `en.json` file should contain nested JSON objects for logical grouping:
  ```json
  {
      "client": {
          "welcome_message": "Welcome to the client!"
      },
      "server": {
          "status": "Server running"
      }
  }
  ```
- To fetch the string, use `locale.get("client.welcome_message")`.

## 4. Parameter Interpolation
- Use `python-i18n` standard formatting parameters.
- Inside JSON: `"welcome": "Welcome, {name}!"`
- Inside Python: `locale.get("client.welcome", name="Alice")`

## 5. Locales
- Currently supported locales: English (`en.json`) and Spanish (`es.json`).
- If you add a new key, you MUST add it to ALL active `.json` localization files simultaneously to prevent fallback rendering gaps.
