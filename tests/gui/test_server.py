"""
Module: test_server.py
───────────────────────
Purpose: Validates the Server Lab View UI, in particular the Socket State
Visualizer panel added to close Epic 8 finding H-003.

Architectural Role:
Acts as the automated validation layer for the server-side frontend UI. It
simulates backend signal emissions without starting a real TCP server, the
same pattern `tests/gui/test_client.py` uses for the client window.

Responsibilities:
- Assert that connecting/disconnecting clients populate and clear the
  Socket States panel.
- Assert that a `socket_state_changed` signal updates an existing entry's
  displayed state (e.g. IDLE -> TRANSFERRING -> IDLE).

Expected Collaborators:
- `pytest-qt` (provides the qtbot).
- `src.ui.server_window` (the subject under test).
"""

import pytest
from src.ui.server_window import ServerWindow


@pytest.fixture
def server_window(qtbot, mocker, qapp):
    """
    Provides an isolated ServerWindow instance for testing.

    Args:
        qtbot: The Pytest-Qt runner for simulating events.
        mocker: The pytest-mock fixture.
        qapp: The QApplication fixture.

    Returns:
        A fully initialized `ServerWindow`.

    Side Effects:
        Instantiates a real `ServerBackend` (no sockets are opened) and
        mocks config/locale/auth/files/runtime dependencies.

    Failure Behavior:
        None.
    """
    config_mock = mocker.MagicMock()
    config_mock.get_nested.side_effect = lambda *keys, default=None: default

    locale_mock = mocker.MagicMock()
    locale_mock.get.side_effect = lambda key, **kwargs: key
    theme_mock = mocker.MagicMock()

    auth_mock = mocker.MagicMock()
    auth_mock.list_users.return_value = []
    files_mock = mocker.MagicMock()

    runtime_mock = mocker.MagicMock()
    runtime_mock.logs_dir = "/tmp"

    from src.network.server_backend import ServerBackend
    real_backend = ServerBackend(auth_mock, files_mock)

    window = ServerWindow(
        config_mock, locale_mock, theme_mock, qapp,
        auth=auth_mock, files=files_mock, backend=real_backend, runtime=runtime_mock,
    )

    qtbot.addWidget(window)
    return window


def test_socket_state_panel_tracks_connect_and_disconnect(server_window):
    """
    Ensures a connecting client appears in the Socket States panel as IDLE,
    and disappears again once it disconnects.
    """
    server_window.backend.client_connected.emit("127.0.0.1:5555")

    assert server_window._socket_states["127.0.0.1:5555"] == "IDLE"
    assert server_window.socket_states_list.count() == 1
    # The locale mock echoes keys back, so the rendered label carries the
    # "socket_state_idle" locale key rather than the raw internal state name.
    assert "socket_state_idle" in server_window.socket_states_list.item(0).text()

    server_window.backend.client_disconnected.emit("127.0.0.1:5555")

    assert "127.0.0.1:5555" not in server_window._socket_states
    assert server_window.socket_states_list.count() == 0


def test_socket_state_panel_reflects_transfer_state(server_window):
    """
    Ensures `socket_state_changed` updates an already-connected client's
    displayed state (e.g. when a transfer starts/stops), and that state
    changes for unknown/already-disconnected addresses are ignored.
    """
    addr = "127.0.0.1:6000"
    server_window.backend.client_connected.emit(addr)

    server_window.backend.socket_state_changed.emit(addr, "TRANSFERRING")
    assert server_window._socket_states[addr] == "TRANSFERRING"
    assert "socket_state_transferring" in server_window.socket_states_list.item(0).text()

    server_window.backend.socket_state_changed.emit(addr, "IDLE")
    assert server_window._socket_states[addr] == "IDLE"

    # A state change for a client that isn't tracked must not resurrect it.
    server_window.backend.socket_state_changed.emit("10.0.0.9:1234", "TRANSFERRING")
    assert "10.0.0.9:1234" not in server_window._socket_states


def test_stopping_server_clears_socket_states(server_window):
    """
    Ensures the Socket States panel is cleared when the server stops, mirroring
    the existing `clients_list.clear()` teardown behavior.
    """
    server_window.backend.client_connected.emit("127.0.0.1:7000")
    assert server_window.socket_states_list.count() == 1

    server_window._on_stopped()

    assert server_window.socket_states_list.count() == 0
    assert server_window._socket_states == {}
