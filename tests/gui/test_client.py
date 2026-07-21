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
    locale_mock.get.side_effect = lambda key, **kwargs: f"{key} {kwargs}" if kwargs else key
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
    assert client_window.download_btn.isEnabled() is False
    assert client_window.rename_btn.isEnabled() is False
    assert client_window.delete_btn.isEnabled() is False


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
    from PyQt6.QtGui import QShortcut

    shortcuts = client_window.findChildren(QShortcut)
    f5_shortcut = next(s for s in shortcuts if s.key().toString() == "F5")

    # We can't use a spy on a previously connected slot easily in PyQt,
    # so we just check if it's connected or emit it and check effects.
    client_window._current_path = "test"

    list_files_spy = mocker.patch.object(client_window.backend, "list_files")
    f5_shortcut.activated.emit()
    list_files_spy.assert_called_once_with("test")


def test_transfer_queue_indicator_visibility(client_window):
    """
    Ensures that transfer rows appear while transfers are active and are
    retired once the transfer reaches a terminal state.

    Uses the real `TransferState` enum values — the engine emits those exact
    strings, so the test also guards the enum/UI contract.
    """
    from src.network.transfer_state import TransferState

    client_window.show()

    assert client_window.transfers_layout.count() == 0

    client_window._transfer_is_upload["file1.bin"] = False
    client_window._on_transfer_state_changed("file1.bin", TransferState.RUNNING.value)
    assert client_window.transfers_layout.count() == 1

    client_window._on_transfer_state_changed("file1.bin", TransferState.COMPLETED.value)

    # Needs a small QTimer delay for the row to be removed
    from pytestqt.qtbot import QtBot

    qtbot = QtBot(client_window)
    qtbot.wait(1600)

    assert client_window.transfers_layout.count() == 0


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


def test_inspector_ping_filter(client_window):
    """Ensures PING messages are hidden by default and shown when toggled."""
    inspector = client_window.inspector
    inspector.log_tx("PING|1234")
    # Default is off, so console is still empty
    assert inspector.console.toPlainText() == ""

    # Toggle on
    inspector.ping_check.setChecked(True)
    assert "PING" in inspector.console.toPlainText()


def test_inspector_clear(client_window):
    """Ensures clear empties the buffer and shows the empty state."""
    client_window.show()
    inspector = client_window.inspector
    inspector.log_tx("LIST|/")
    assert "LIST" in inspector.console.toPlainText()
    assert inspector.empty_state.isVisibleTo(inspector) is False

    inspector.clear_btn.clicked.emit()
    assert "LIST" not in inspector.console.toPlainText()
    assert inspector.empty_state.isVisibleTo(inspector) is True


def test_inspector_click_to_explain(client_window):
    """Ensures clicking a known command updates the explanation label."""
    client_window.show()
    inspector = client_window.inspector
    inspector.log_tx("AUTH|user|pass")

    # Simulate a cursor block selection matching the log line
    cursor = inspector.console.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    inspector.console.setTextCursor(cursor)

    # Trigger the signal
    inspector._on_selection_changed()
    assert "AUTH" in inspector.explanation_label.text()


def test_mint_dialog_get_text(mocker, qapp):
    from src.ui.widgets.atoms import MintDialog
    from PyQt6.QtWidgets import QDialog

    mocker.patch.object(MintDialog, "exec", return_value=QDialog.DialogCode.Accepted)
    text, ok = MintDialog.get_text(None, "mint_light", "Title", "Label")
    assert ok is True


def test_mint_dialog_confirm_danger(qapp):
    from src.ui.widgets.atoms import MintDialog
    from PyQt6.QtWidgets import QDialog

    old_exec = MintDialog.exec
    was_danger = False

    def mock_exec(self):
        nonlocal was_danger
        was_danger = self.confirm_btn.objectName() == "dangerButton"
        return QDialog.DialogCode.Accepted

    MintDialog.exec = mock_exec
    try:
        ok = MintDialog.confirm(None, "mint_light", "Title", "Msg", danger=True)
        assert ok is True
        assert was_danger is True
    finally:
        MintDialog.exec = old_exec
