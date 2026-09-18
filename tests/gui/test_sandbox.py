"""
GUI tests for SandboxWindow and Launcher Sandbox Mode.
"""

from PyQt6.QtWidgets import QSplitter
from src.ui.launcher import LauncherWindow
from src.ui.sandbox_window import SandboxWindow


def test_launcher_renders_sandbox_mode(qtbot, mocker, qapp):
    config_mock = mocker.MagicMock()
    config_mock.get.return_value = "mint_light"
    locale_mock = mocker.MagicMock()
    locale_mock.get.side_effect = lambda key, **kwargs: key
    locale_mock.current_locale = "en"
    theme_mock = mocker.MagicMock()

    launcher = LauncherWindow(config_mock, locale_mock, theme_mock, qapp)
    qtbot.addWidget(launcher)

    assert hasattr(launcher, "sandbox_btn")
    assert launcher.sandbox_btn is not None
    assert launcher.sandbox_btn.text() == "launcher.start_sandbox"


def test_sandbox_window_structure(qtbot, mocker, qapp, tmp_path):
    config_mock = mocker.MagicMock()
    config_mock.get.return_value = "mint_light"
    config_mock.get_nested.side_effect = lambda *args, **kwargs: kwargs.get("default", "127.0.0.1")

    locale_mock = mocker.MagicMock()
    locale_mock.get.side_effect = lambda key, **kwargs: key

    theme_mock = mocker.MagicMock()

    runtime_mock = mocker.MagicMock()
    runtime_mock.config_dir = tmp_path / "config"
    runtime_mock.sandboxes_dir = tmp_path / "sandboxes"
    runtime_mock.logs_dir = tmp_path / "logs"
    runtime_mock.config_dir.mkdir(parents=True, exist_ok=True)
    runtime_mock.sandboxes_dir.mkdir(parents=True, exist_ok=True)
    runtime_mock.logs_dir.mkdir(parents=True, exist_ok=True)

    sandbox = SandboxWindow(config_mock, locale_mock, theme_mock, qapp, runtime=runtime_mock)
    qtbot.addWidget(sandbox)

    assert isinstance(sandbox.splitter, QSplitter)
    assert sandbox.server_win is not None
    assert sandbox.client_win is not None
    assert sandbox.quick_connect_btn is not None
    assert sandbox.server_win.host_input.text() == "127.0.0.1"
    assert sandbox.client_win.host_input.text() == "127.0.0.1"
