"""
Module: test_client.py
──────────────────────
Purpose: Validates the user interface using pytest-qt.

Architectural Role:
Acts as the automated validation layer for the frontend UI. It simulates user 
clicks and tests signal-slot interactions without starting a real TCP server.

Responsibilities:
- Assert that UI widgets correctly enable/disable based on connection state.
- Assert that backend errors are visibly rendered in the GUI.

Expected Collaborators:
- `pytest-qt` (provides the qtbot).
- `src.ui.client_window` (the subject under test).
"""

import pytest
from PyQt6.QtCore import Qt
from src.ui.client_window import ClientWindow


@pytest.fixture
def client_window(qtbot, mocker, qapp):
    """
    Provides an isolated ClientWindow instance for testing.

    Args:
        qtbot: The Pytest-Qt runner for simulating events.
        mocker: The pytest-mock fixture.
        qapp: The QApplication fixture.

    Returns:
        A fully initialized `ClientWindow`.

    Side Effects:
        Instantiates a `ClientBackend` and mocks config/locale data.

    Failure Behavior:
        None.
    """
    config_mock = mocker.MagicMock()
    config_mock.get_nested.return_value = "localhost"
    
    locale_mock = mocker.MagicMock()
    # Echoes the key back (so assertions can match on it) but still
    # interpolates kwargs like the real LocaleManager, since several
    # windows format dynamic values (codes, counts, hosts) into their
    # locale strings.
    locale_mock.get.side_effect = lambda key, **kwargs: (
        f"{key} {kwargs}" if kwargs else key
    )
    theme_mock = mocker.MagicMock()
    
    from src.network.client_backend import ClientBackend
    real_backend = ClientBackend()

    window = ClientWindow(config_mock, locale_mock, theme_mock, qapp, backend=real_backend)
    
    qtbot.addWidget(window)
    return window


def test_initial_ui_state(client_window):
    """
    Ensures that widgets are locked before a connection is established.

    Args:
        client_window: The isolated UI fixture.

    Returns:
        None.

    Side Effects:
        None.

    Failure Behavior:
        Fails if download/upload buttons are incorrectly enabled.
    """
    assert client_window.connection_toggle_btn.isChecked() is False
    assert client_window.upload_btn.isEnabled() is False
    assert client_window.download_btn.isEnabled() is False
    assert client_window.host_input.isEnabled() is True


def test_ui_state_transitions_on_auth(qtbot, client_window, mocker):
    """
    Ensures that a successful connection unlocks the file operation UI.

    Args:
        qtbot: The UI interaction bot.
        client_window: The isolated UI fixture.
        mocker: The pytest-mock fixture.

    Returns:
        None.

    Side Effects:
        Simulates a mouse click.
        Forces the emission of a Qt signal (`auth_success`).

    Failure Behavior:
        Fails if the connect button remains enabled after login.
    """
    # Mock backend to simulate immediate connection
    mocker.patch.object(client_window.backend, "connect_to_server")

    # Simulate clicking the connection toggle (off -> on triggers connect)
    qtbot.mouseClick(client_window.connection_toggle_btn, Qt.MouseButton.LeftButton)
    client_window.backend.connect_to_server.assert_called_once()

    # Emit auth_success to trigger UI transition
    client_window.backend.auth_success.emit()

    assert client_window.host_input.isEnabled() is False
    assert client_window.connection_toggle_btn.isChecked() is True
    assert client_window.upload_btn.isEnabled() is True
    assert client_window.download_btn.isEnabled() is True


def test_f5_shortcut_triggers_refresh(qtbot, client_window, mocker):
    """
    Regression test for the Quick Win: F5 must refresh the directory listing.

    Args:
        qtbot: The UI interaction bot.
        client_window: The isolated UI fixture.
        mocker: The pytest-mock fixture.

    Failure Behavior:
        Fails if pressing F5 does not call `_refresh`.
    """
    refresh_spy = mocker.patch.object(client_window, "_refresh")

    qtbot.keyClick(client_window, Qt.Key.Key_F5)

    refresh_spy.assert_called_once()


def test_transfer_queue_indicator_visibility(client_window):
    """
    Ensures the queue indicator label appears while transfers are active
    (per the engine's `active_transfers` registry) and hides once empty.
    """
    client_window.show()
    engine = client_window.backend.engine
    assert client_window.queue_label.isVisible() is False

    engine.active_transfers["file1.bin"] = object()
    client_window._on_transfer_state_changed("file1.bin", "Running")
    assert client_window.queue_label.isVisible() is True
    assert "1" in client_window.queue_label.text()

    engine.active_transfers.pop("file1.bin")
    client_window._on_transfer_state_changed("file1.bin", "Completed")
    assert client_window.queue_label.isVisible() is False


def test_ui_status_bar_updates_on_error(client_window):
    """
    Ensures that backend errors are displayed in the status bar.

    Args:
        client_window: The isolated UI fixture.

    Returns:
        None.

    Side Effects:
        Forces the emission of an `error_occurred` Qt signal.

    Failure Behavior:
        Fails if the status bar text doesn't contain the error details.
    """
    client_window.backend.error_occurred.emit("AuthFailed", "Wrong password")
    
    current_message = client_window.status_bar.currentMessage()
    assert "AuthFailed" in current_message
    assert "Wrong password" in current_message
