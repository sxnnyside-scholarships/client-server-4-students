"""
Module: test_regression.py
──────────────────────────
Purpose: Validates fixes for previously discovered defects to ensure they do not regress.

Architectural Role:
Acts as the forensic validation suite. While `test_protocol` checks "happy paths,"
this file specifically exercises edge-cases that previously broke the application
(e.g., brute force limits, sudden disconnects).

Responsibilities:
- Verify that `max_connections` bounds are strictly enforced.
- Verify that bad authentication attempts trigger an IP ban and socket drop.
- Verify that mid-transfer disconnects do not throw fatal OSErrors.

Expected Collaborators:
- `pytest` (test runner).
- `src.network.server_backend.ServerBackend` (the local test server).
"""

import socket
import time

import pytest

from src.core.protocol import CMD_AUTH, ProtocolHandler
from src.network.server_backend import ServerBackend
from src.network.client_backend import ClientBackend


@pytest.mark.skip(reason="Locally unstable due to macOS SIP threading limits")
def test_regression_max_connections(server_backend: ServerBackend):
    """
    Ensures the server enforces its maximum concurrent connection limit.

    Args:
        server_backend: The running test server fixture.

    Returns:
        None.

    Side Effects:
        Spawns multiple raw TCP sockets.

    Failure Behavior:
        Fails if the server accepts the 3rd connection instead of sending an -ERR string.

    Defect: Server used to accept unlimited connections.
    Fix: Epic 3 bounded connections to `max_connections`.
    Verification: Exhaust the connection pool and assert the next socket is rejected.
    """
    server_backend.max_connections = 2
    port = server_backend.engine._socket.getsockname()[1]

    sockets = []

    # Fill the slots
    for _ in range(2):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", port))
        sockets.append(s)

    time.sleep(0.5)  # Let server process accept()

    # 3rd connection should be instantly rejected
    s3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s3.connect(("127.0.0.1", port))

    response = s3.recv(1024).decode()
    assert "-ERR Maximum connections exceeded" in response

    for s in sockets:
        s.close()
    s3.close()


def test_regression_auth_brute_force_drop(server_backend: ServerBackend):
    """
    Ensures the server drops the socket after 5 failed authentication attempts.

    Args:
        server_backend: The running test server fixture.

    Returns:
        None.

    Side Effects:
        Spawns a raw TCP socket.
        Forces an IP ban inside the server's security context.

    Failure Behavior:
        Fails if the 6th command does not trigger a socket exception (meaning it wasn't dropped).

    Defect: Clients could spam AUTH forever.
    Fix: Epic 3 added a 5-strike rate limiter for Auth.
    Verification: Send 5 bad passwords. The socket should be closed by the server.
    """
    port = server_backend.engine._socket.getsockname()[1]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", port))
    proto = ProtocolHandler(s)

    # Handshake
    proto.send_message("HELLO", "CS4S/2.0")
    proto.recv_message()

    for _ in range(5):
        proto.send_message(CMD_AUTH, "testuser", "badpass")
        proto.recv_message()

    # The 6th attempt should fail due to socket closure
    try:
        proto.send_message(CMD_AUTH, "testuser", "badpass")
        proto.recv_message()
        pytest.fail("Socket should have been closed")
    except (ConnectionError, OSError, EOFError, IndexError):
        pass
    finally:
        s.close()


def test_regression_mid_transfer_disconnect_does_not_crash(
    qtbot, server_backend: ServerBackend, client_backend: ClientBackend, tmp_path
):
    """
    Ensures that disconnecting during an active byte stream is handled gracefully.

    Args:
        qtbot: The Pytest-Qt signal watcher.
        server_backend: The running test server fixture.
        client_backend: The isolated client fixture.
        tmp_path: The Pytest temporary directory fixture.

    Returns:
        None.

    Side Effects:
        Creates a 5MB dummy file on disk.
        Triggers `client_backend.disconnect()` asynchronously.

    Failure Behavior:
        Fails if an unhandled Python exception crashes the thread.

    Defect: Disconnecting while uploading threw unhandled OSErrors.
    Fix: Epic 2 added `_shutdown_event` checks.
    Verification: Start a large upload and immediately call disconnect().
    Client should not crash and should enter the disconnected state.
    """
    port = server_backend.engine._socket.getsockname()[1]
    client_backend.connect_to_server("127.0.0.1", port, "testuser", "testpass")
    qtbot.waitUntil(lambda: client_backend.is_connected)

    # Create a 5MB dummy file
    local_source = tmp_path / "large.bin"
    with open(local_source, "wb") as f:
        f.write(b"0" * (1024 * 1024 * 5))

    # Start upload
    client_backend.upload_file(str(local_source), "large.bin")
    time.sleep(0.1)  # Let the background thread start the loop

    # Interrupt it
    client_backend.disconnect()

    assert client_backend.is_connected is False
    # If the thread crashed, pytest will fail when catching unhandled thread exceptions.
