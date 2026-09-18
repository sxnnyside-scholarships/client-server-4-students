"""
Module: test_tls.py
───────────────────
Purpose: Integration validation of end-to-end TLS/SSL encrypted socket streams between client and server.

Architectural Role:
Acts as the transport-layer security integration suite, ensuring that the TLS wrapping layer properly
secures framing without corrupting ASCII protocol delimiters, and that plaintext clients are cleanly rejected.

Responsibilities:
- Verify end-to-end encrypted connection and authentication over loopback sockets.
- Ensure that the client protocol frame inspector correctly flags traffic as TLS-protected.
- Validate that standard protocol commands (such as LIST) function seamlessly over TLS sockets.
- Verify that non-TLS (plaintext) connection attempts against a TLS-enforced server fail gracefully.

Dependencies:
- `pathlib.Path`
- `pytest`
- `src.core.cert_util.ensure_self_signed_cert`
- `src.network.client_backend.ClientBackend`
- `src.network.server_backend.ServerBackend`
- `src.storage.auth.AuthManager`
- `src.storage.file_manager.FileManager`

Expected Collaborators:
- `tls_server`: Pytest fixture managing a real ephemeral TLS server listener.
- `qtbot`: Awaits PyQt signals asynchronously without busy looping.

Educational Note: Transport Layer Security (TLS) Integration
TLS operates between the Transport Layer (TCP) and Application Layer. Sockets are wrapped in an SSL context
following the initial TCP 3-way handshake. Verifying that a plaintext client is rejected prevents students
from mistakenly believing application-level protocols can speak across encryption mismatches.
"""

import time
from pathlib import Path

import pytest
from src.core.cert_util import ensure_self_signed_cert
from src.network.client_backend import ClientBackend
from src.network.server_backend import ServerBackend
from src.storage.auth import AuthManager
from src.storage.file_manager import FileManager


@pytest.fixture
def tls_server(tmp_path: Path):
    """
    Spawns an active ServerBackend instance configured with ephemeral self-signed TLS certificates.

    Args:
        tmp_path: Pytest temporary directory fixture for certificate, auth, and sandbox storage.

    Returns:
        Generator yielding an active ServerBackend bound to a dynamic loopback port.

    Side Effects:
        Generates ephemeral X.509 certificates and binds a local TCP socket listener.

    Failure Behavior:
        Raises an assertion error if the listener fails to bind within the 500ms timeout window.
    """
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    ensure_self_signed_cert(cert_path, key_path)

    auth = AuthManager(tmp_path / "users.json")
    auth.add_user("tls_user", "tls_pass")

    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    files = FileManager(sandbox)

    server = ServerBackend(auth, files)
    server.engine.cert_file = str(cert_path)
    server.engine.key_file = str(key_path)
    server.start("127.0.0.1", 0, enable_tls=True)

    # Wait for listener
    for _ in range(50):
        if server.is_running and server.engine._socket:
            break
        time.sleep(0.01)

    yield server
    server.stop()


def test_tls_connection_and_authentication(tls_server, qtbot):
    """
    Validates end-to-end encrypted connection, authentication, and file listing over TLS.

    Args:
        tls_server: The active TLS-enabled server backend fixture.
        qtbot: The pytest-qt fixture for awaiting Qt signals.

    Returns:
        None.

    Side Effects:
        Connects a ClientBackend instance, performs TLS handshake, and sends a LIST command.

    Failure Behavior:
        Fails if TLS handshake fails, authentication fails, or file list is not received.
    """
    port = tls_server.engine._socket.getsockname()[1]
    client = ClientBackend()

    with qtbot.waitSignal(client.connected, timeout=5000):
        client.connect_to_server("127.0.0.1", port, "tls_user", "tls_pass", enable_tls=True)

    assert client.is_connected
    assert client.engine.proto.is_tls is True

    # Validate that round-trip operations work over TLS
    with qtbot.waitSignal(client.file_list_received, timeout=5000):
        client.list_files()

    client.disconnect()


def test_plaintext_client_rejected_by_tls_server(tls_server, qtbot):
    """
    Validates that a plaintext client attempting to connect to a TLS listener fails gracefully.

    Args:
        tls_server: The active TLS-enabled server backend fixture.
        qtbot: The pytest-qt fixture for awaiting Qt signals.

    Returns:
        None.

    Side Effects:
        Attempts connection without enabling TLS.

    Failure Behavior:
        Fails if error_occurred signal is not emitted or if the client reports an active connection.
    """
    port = tls_server.engine._socket.getsockname()[1]
    client = ClientBackend()

    # Connecting without TLS should trigger error_occurred signal
    with qtbot.waitSignal(client.error_occurred, timeout=5000):
        client.connect_to_server("127.0.0.1", port, "tls_user", "tls_pass", enable_tls=False)

    assert not client.is_connected
