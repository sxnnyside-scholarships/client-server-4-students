import csv
from unittest.mock import MagicMock, patch
from src.core.config import ConfigManager
from src.localization.locale_manager import LocaleManager
from src.network.client_backend import ClientBackend
from src.network.server_backend import ServerBackend
from src.storage.auth import AuthManager
from src.storage.file_manager import FileManager
from src.ui.client_window import ClientWindow
from src.ui.server_window import ServerWindow
from src.ui.themes.theme_manager import ThemeManager


def test_server_broadcast_ui(qtbot, qapp, tmp_path):
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

    with patch("PyQt6.QtWidgets.QFileDialog.getOpenFileName", return_value=(str(csv_path), "CSV Files (*.csv)")):
        with patch("src.ui.widgets.atoms.MintDialog.message") as mock_msg:
            window.import_csv_btn.click()
            assert "student_charlie" in auth.users
            mock_msg.assert_called_once()


def test_client_broadcast_received_dialog(qtbot, qapp, tmp_path):
    config = ConfigManager(tmp_path / "config.json")
    locale = LocaleManager("src/localization")
    themes = ThemeManager("src/ui/themes")
    backend = ClientBackend()

    window = ClientWindow(config, locale, themes, qapp, backend=backend)
    qtbot.addWidget(window)

    with patch("src.ui.widgets.atoms.MintDialog.message") as mock_msg:
        backend.broadcast_received.emit("Welcome to Networking Lab!")
        mock_msg.assert_called_once_with(
            window,
            window._theme_name,
            locale.get("client.broadcast_alert_title"),
            "Welcome to Networking Lab!",
        )
