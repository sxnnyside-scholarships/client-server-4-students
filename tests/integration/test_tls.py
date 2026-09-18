"""
Integration tests for TLS/SSL encrypted client-server connections.
Validates end-to-end encrypted transport, authentication, and plaintext rejection.
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
    Spawns a ServerBackend with TLS enabled using self-signed certificates.
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
    Validates that a TLS-enabled client successfully connects and authenticates
    with a TLS-enabled server, and that protocol traffic is marked as encrypted.
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
    """
    port = tls_server.engine._socket.getsockname()[1]
    client = ClientBackend()

    # Connecting without TLS should trigger error_occurred signal
    with qtbot.waitSignal(client.error_occurred, timeout=5000):
        client.connect_to_server("127.0.0.1", port, "tls_user", "tls_pass", enable_tls=False)

    assert not client.is_connected
