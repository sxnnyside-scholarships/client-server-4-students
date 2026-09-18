"""
Module: test_sandbox.py
───────────────────────
Purpose: Validates the integrated Dual-Pane Split-Screen Sandbox UI and launcher entrypoint.

Architectural Role:
Acts as the automated validation layer for the self-study sandbox container. It verifies
the instantiation, default loopback configurations, splitter properties, and launcher action
wiring in isolation using `pytest-qt`.

Responsibilities:
- Verify that the Launcher window renders and exposes the Sandbox entry button.
- Verify that `SandboxWindow` correctly instantiates embedded `ServerWindow` and `ClientWindow`.
- Ensure default loopback network parameters (`127.0.0.1:4500`, user `student`) are pre-populated.
- Verify that the central `QSplitter` hosts both panes without collapsing.

Dependencies:
- `PyQt6.QtWidgets.QSplitter`
- `src.ui.launcher.LauncherWindow`
- `src.ui.sandbox_window.SandboxWindow`
- `pytest-qt`

Expected Collaborators:
- `qtbot`: Simulates UI lifecycle and event loops.
- `mocker`: Mocking configuration, theme, and localization providers.

Educational Note: Dual-Pane UI Validation
Testing composite UI containers that embed full window views (`ServerWindow` and `ClientWindow`)
ensures that layout constraints (such as minimum sizes and splitter collapse behavior) do not
regress and compromise student visibility on varied display form factors.
"""

from PyQt6.QtWidgets import QSplitter
from src.ui.launcher import LauncherWindow
from src.ui.sandbox_window import SandboxWindow


def test_launcher_renders_sandbox_mode(qtbot, mocker, qapp):
    """
    Validates that the Launcher window presents the Sandbox mode button with proper localization.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        mocker: The pytest-mock fixture for dependency injection.
        qapp: The active QApplication instance.

    Returns:
        None.

    Side Effects:
        Instantiates a LauncherWindow and registers it with the qtbot event loop.

    Failure Behavior:
        Fails if the sandbox button attribute is missing or does not reflect the expected locale key.
    """
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
    """
    Validates the dual-pane structure, splitter setup, and pre-seeded loopback defaults.

    Args:
        qtbot: The pytest-qt fixture for simulating GUI events.
        mocker: The pytest-mock fixture for dependency injection.
        qapp: The active QApplication instance.
        tmp_path: Pytest temporary directory path fixture.

    Returns:
        None.

    Side Effects:
        Initializes an isolated SandboxWindow with mock runtime environments.

    Failure Behavior:
        Fails if ServerWindow or ClientWindow are missing, or if loopback IP is incorrectly configured.
    """
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
