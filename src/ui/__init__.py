"""
Package: src.ui
───────────────
Purpose: Provides all graphical user interface (GUI) windows and dialogs for the CS4S application.

Architectural Role:
Acts as the presentation layer. This package is strictly forbidden from directly executing
network I/O or disk I/O. It instantiates backend components via Dependency Injection and
interacts with them entirely through PyQt6 signals and slots.

Responsibilities:
- Render the Launcher, Client, and Server windows.
- Capture user input and translate it into backend command requests.
- Observe backend state changes (e.g., download progress) and update visual indicators.

Public API:
- `launcher.LauncherWindow`: The initial boot screen to select the application mode.
- `client_window.ClientWindow`: The main graphical client interface.
- `server_window.ServerWindow`: The main graphical server management console.

Expected Collaborators:
- `src.network`: Consumed to trigger connections and file transfers.
- `src.localization`: Consumed to populate all text labels dynamically.
- `src.ui.widgets`: Consumed to compose complex visual layouts.
"""
