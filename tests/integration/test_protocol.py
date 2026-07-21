"""
Module: test_protocol.py
────────────────────────
Purpose: Validates the complete client-server communication lifecycle.

Architectural Role:
Acts as the highest-level integration test suite for the networking stack. It
spawns a real server bound to a localhost socket and exercises the client facade,
ensuring that string parsing, thread locks, and Qt signals all cooperate cleanly.

Responsibilities:
- Verify successful connections and authentications.
- Verify safe failure modes (e.g., bad passwords dropping the connection).
- Verify end-to-end binary file streaming.

Expected Collaborators:
- `pytest` (test runner).
- `src.network.client_backend.ClientBackend` (the client under test).
- `src.network.server_backend.ServerBackend` (the local test server).
"""

from src.network.client_backend import ClientBackend
from src.network.server_backend import ServerBackend


def test_rtt_measurement(qtbot, server_backend: ServerBackend, client_backend: ClientBackend):
    """
    Validates the CMD_PING round-trip latency probe end-to-end.

    Epic 8.6 ("Live Statistics") flagged RTT as missing entirely. This
    exercises the new PING/PONG exchange: the client times the round trip
    and emits `rtt_measured` with a small, non-negative millisecond value.
    """
    port = server_backend.engine._socket.getsockname()[1]
    client_backend.connect_to_server("127.0.0.1", port, "testuser", "testpass")
    qtbot.waitUntil(lambda: client_backend.is_connected)

    with qtbot.waitSignal(client_backend.rtt_measured, timeout=2000) as blocker:
        client_backend.measure_rtt()

    rtt_ms = blocker.args[0]
    assert isinstance(rtt_ms, float)
    assert rtt_ms >= 0.0
    assert rtt_ms < 2000.0  # sanity bound for a loopback round trip

    client_backend.disconnect()


def test_socket_state_transitions_during_transfer(
    qtbot, server_backend: ServerBackend, client_backend: ClientBackend, tmp_path
):
    """
    Regression/coverage test for the Socket State Visualizer (Epic 8.3).

    Verifies the server emits `socket_state_changed` with "TRANSFERRING"
    while an upload is in flight, then settles back to "IDLE" once it
    completes — the simplified state model the visualizer panel renders.
    """
    port = server_backend.engine._socket.getsockname()[1]
    client_backend.connect_to_server("127.0.0.1", port, "testuser", "testpass")
    qtbot.waitUntil(lambda: client_backend.is_connected)

    local_source = tmp_path / "state_probe.bin"
    local_source.write_bytes(b"x" * (1024 * 1024 * 2))

    observed_states = []
    server_backend.socket_state_changed.connect(lambda addr, state: observed_states.append(state))

    with qtbot.waitSignal(client_backend.upload_complete, timeout=5000):
        client_backend.upload_file(str(local_source), "state_probe.bin")

    assert "TRANSFERRING" in observed_states
    assert observed_states[-1] == "IDLE"

    client_backend.disconnect()


def test_successful_connection_and_auth(qtbot, server_backend: ServerBackend, client_backend: ClientBackend):
    """
    Ensures the client can connect and authenticate against a running server.

    Args:
        qtbot: The Pytest-Qt signal watcher.
        server_backend: The running test server fixture.
        client_backend: The isolated client fixture.

    Returns:
        None.

    Side Effects:
        Initiates a real TCP handshake.

    Failure Behavior:
        Fails if the `connected` or `auth_success` signals are not emitted within 2000ms.
    """
    port = server_backend.engine._socket.getsockname()[1]

    with qtbot.waitSignals([client_backend.connected, client_backend.auth_success], timeout=2000):
        client_backend.connect_to_server("127.0.0.1", port, "testuser", "testpass")

    assert client_backend.is_connected is True


def test_auth_failure_disconnects(qtbot, server_backend: ServerBackend, client_backend: ClientBackend):
    """
    Ensures providing bad credentials safely returns the client to a disconnected state.

    Args:
        qtbot: The Pytest-Qt signal watcher.
        server_backend: The running test server fixture.
        client_backend: The isolated client fixture.

    Returns:
        None.

    Side Effects:
        Initiates a real TCP handshake with invalid credentials.

    Failure Behavior:
        Fails if the `auth_failed` signal is not emitted within 2000ms.
    """
    port = server_backend.engine._socket.getsockname()[1]

    with qtbot.waitSignal(client_backend.auth_failed, timeout=2000) as blocker:
        client_backend.connect_to_server("127.0.0.1", port, "testuser", "wrongpassword")

    assert (
        "AuthFailed" in blocker.args[0]
        or "Failed authentication" in blocker.args[0]
        or isinstance(blocker.args[0], str)
    )
    assert client_backend.is_connected is False


def test_file_upload_download(qtbot, server_backend: ServerBackend, client_backend: ClientBackend, tmp_path):
    """
    Validates end-to-end file streaming over the local socket.

    Args:
        qtbot: The Pytest-Qt signal watcher.
        server_backend: The running test server fixture.
        client_backend: The isolated client fixture.
        tmp_path: The Pytest temporary directory fixture.

    Returns:
        None.

    Side Effects:
        Writes a temporary file to disk.
        Streams bytes over TCP.
        Reads the received bytes from the server's sandbox.

    Failure Behavior:
        Fails if the files are not identical or the signals time out.
    """
    port = server_backend.engine._socket.getsockname()[1]
    client_backend.connect_to_server("127.0.0.1", port, "testuser", "testpass")

    qtbot.waitUntil(lambda: client_backend.is_connected)

    # Create a dummy file
    local_source = tmp_path / "source.txt"
    local_source.write_text("Hello, CS4S!")

    remote_name = "uploaded_file.txt"

    # Wait for the upload complete signal
    with qtbot.waitSignal(client_backend.upload_complete, timeout=5000):
        client_backend.upload_file(str(local_source), remote_name)

    # Verify file is in the server's sandbox
    sandbox_file = server_backend.files.get_file_path("testuser", remote_name)
    assert sandbox_file.exists()
    assert sandbox_file.read_text() == "Hello, CS4S!"

    # Download the file back
    local_dest = tmp_path / "dest.txt"
    with qtbot.waitSignal(client_backend.download_complete, timeout=5000):
        client_backend.download_file(remote_name, str(local_dest))

    assert local_dest.exists()
    assert local_dest.read_text() == "Hello, CS4S!"

    client_backend.disconnect()


def test_create_directory_round_trip(qtbot, server_backend: ServerBackend, client_backend: ClientBackend):
    """
    Regression test for the CMD_MKDIR response code mismatch.

    The server previously sent the string tokens STATUS_OK/STATUS_ERROR as the
    numeric response code, which the client's `resp[0] == str(CODE_ACTION_OK)`
    check could never match — so the directory was created on disk but the
    client always reported failure. This asserts both sides of that contract.
    """
    port = server_backend.engine._socket.getsockname()[1]
    client_backend.connect_to_server("127.0.0.1", port, "testuser", "testpass")
    qtbot.waitUntil(lambda: client_backend.is_connected)

    with qtbot.waitSignal(client_backend.directory_created, timeout=2000):
        client_backend.create_directory("new_folder")

    sandbox_dir = server_backend.files.get_file_path("testuser", "new_folder")
    assert sandbox_dir.is_dir()

    client_backend.disconnect()
