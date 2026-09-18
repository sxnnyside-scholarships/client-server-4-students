"""
Module: test_server_teacher_tools.py
────────────────────────────────────
Purpose: Validates the educator management tools in the Server UI (broadcast messaging and CSV student import)
and the corresponding alert notification presentation on connected clients.

Architectural Role:
Acts as the test suite for teacher-oriented administrative features, verifying that instructors can push
live notifications to all connected terminals and perform bulk credential onboarding via standard CSV files.

Responsibilities:
- Verify that the Server window's Lab Mode exposes broadcast text input and triggers backend broadcast.
- Ensure broadcast text inputs clear properly after transmission.
- Verify bulk student onboarding via CSV file selection in the Server User Management view.
- Verify that Client windows display an alert dialog upon receiving a broadcast notification signal.

Dependencies:
- `csv`
- `unittest.mock`
- `PyQt6.QtWidgets.QFileDialog`
- `src.core.config.ConfigManager`
- `src.localization.locale_manager.LocaleManager`
- `src.network.client_backend.ClientBackend`
- `src.network.server_backend.ServerBackend`
- `src.storage.auth.AuthManager`
- `src.storage.file_manager.FileManager`
- `src.ui.client_window.ClientWindow`
- `src.ui.server_window.ServerWindow`
- `src.ui.themes.theme_manager.ThemeManager`
- `src.ui.widgets.atoms.MintDialog`

Expected Collaborators:
- `qtbot`: Simulates UI lifecycle and event loops.
- `mock_msg`: Intercepts modal dialog presentations.

Educational Note: Instructor Administrative Controls
In lab teaching environments, instructors require the ability to announce time limits, instructions,
or emergency server restarts simultaneously across all student machines without accessing external chat apps.
"""

import csv
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QFileDialog
from src.core.config import ConfigManager
from src.localization.locale_manager import LocaleManager
from src.network.client_backend import ClientBackend
from src.network.server_backend import ServerBackend
from src.storage.auth import AuthManager
from src.storage.file_manager import FileManager
from src.ui.client_window import ClientWindow
from src.ui.server_window import ServerWindow
from src.ui.themes.theme_manager import ThemeManager
from src.ui.widgets.atoms import MintDialog


def test_server_broadcast_ui(qtbot, qapp, tmp_path):
    """
    Validates that the Server Lab Mode interface provides broadcast message controls and routes text to backend.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        qapp: The active QApplication instance.
        tmp_path: Temporary filesystem path fixture.

    Returns:
        None.

    Side Effects:
        Fires broadcast action through ServerWindow UI widgets.

    Failure Behavior:
        Fails if backend.broadcast_message is not called with the entered text or if the input fails to clear.
    """
    config = ConfigManager(tmp_path / "config.json")
    locale = LocaleManager("src/localization")
    themes = ThemeManager("src/ui/themes")
    auth = AuthManager(tmp_path / "users.json")
    files = FileManager(tmp_path / "files")
    backend = ServerBackend(auth, files)
    backend.broadcast_message = MagicMock(return_value=3)

    window = ServerWindow(config, locale, themes, qapp, backend=backend, auth=auth, files=files)
    qtbot.addWidget(window)

    window._on_mode_changed("lab")
    assert window.stack.currentWidget() == window.lab_page

    assert hasattr(window, "broadcast_input")
    assert hasattr(window, "broadcast_btn")

    window.broadcast_input.setText("Notice: System maintenance in 5m")
    window.broadcast_btn.click()

    backend.broadcast_message.assert_called_once_with("Notice: System maintenance in 5m")
    assert window.broadcast_input.text() == ""


def test_server_import_csv_ui(qtbot, qapp, tmp_path):
    """
    Validates CSV file selection dialog integration and batch student credential ingestion in the Server UI.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        qapp: The active QApplication instance.
        tmp_path: Temporary filesystem path fixture for CSV generation and storage.

    Returns:
        None.

    Side Effects:
        Writes a temporary CSV file and populates the server AuthManager storage.

    Failure Behavior:
        Fails if users listed in the CSV are not present in the AuthManager dictionary after import.
    """
    config = ConfigManager(tmp_path / "config.json")
    locale = LocaleManager("src/localization")
    themes = ThemeManager("src/ui/themes")
    auth = AuthManager(tmp_path / "users.json")
    files = FileManager(tmp_path / "files")
    backend = ServerBackend(auth, files)

    window = ServerWindow(config, locale, themes, qapp, backend=backend, auth=auth, files=files)
    qtbot.addWidget(window)

    window._on_mode_changed("users")
    assert window.stack.currentWidget() == window.users_page
    assert hasattr(window, "import_csv_btn")

    # Create dummy csv
    csv_path = tmp_path / "students.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["username", "password"])
        writer.writerow(["student_charlie", "pwd_charlie"])

    with patch.object(QFileDialog, "getOpenFileName", return_value=(str(csv_path), "CSV Files (*.csv)")):
        with patch.object(MintDialog, "message") as mock_msg:
            window.import_csv_btn.click()
            assert "student_charlie" in auth.users
            mock_msg.assert_called_once()


def test_client_broadcast_received_dialog(qtbot, qapp, tmp_path):
    """
    Validates that connected Client windows display an alert dialog upon receiving a broadcast notification.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        qapp: The active QApplication instance.
        tmp_path: Temporary filesystem path fixture.

    Returns:
        None.

    Side Effects:
        Emits `broadcast_received` signal from the client backend.

    Failure Behavior:
        Fails if MintDialog.message is not invoked with the exact broadcast text content.
    """
    config = ConfigManager(tmp_path / "config.json")
    locale = LocaleManager("src/localization")
    themes = ThemeManager("src/ui/themes")
    backend = ClientBackend()

    window = ClientWindow(config, locale, themes, qapp, backend=backend)
    qtbot.addWidget(window)

    with patch.object(MintDialog, "message") as mock_msg:
        backend.broadcast_received.emit("Welcome to Networking Lab!")
        mock_msg.assert_called_once_with(
            window,
            window._theme_name,
            locale.get("client.broadcast_alert_title"),
            "Welcome to Networking Lab!",
        )
