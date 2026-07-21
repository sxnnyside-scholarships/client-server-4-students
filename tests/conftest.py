"""
Module: conftest.py
───────────────────
Purpose: Reusable test utilities, temporary resources, and mock environments.

Architectural Role:
Provides Pytest fixtures injected into all test suites. It handles the teardown
and isolation of disk-bound classes (like `FileManager` and `AuthManager`) to
ensure tests are stateless.

Responsibilities:
- Create isolated temporary directories for filesystem operations.
- Spin up ephemeral `ServerBackend` instances for integration tests.

Expected Collaborators:
- `pytest` (consumes these fixtures automatically).
"""

import time
from pathlib import Path

import pytest
from src.network.client_backend import ClientBackend
from src.network.server_backend import ServerBackend
from src.storage.auth import AuthManager
from src.storage.file_manager import FileManager


@pytest.fixture
def tmp_sandbox(tmp_path: Path) -> Path:
    """
    Provides a temporary, isolated base directory for FileManager.

    Args:
        tmp_path: The built-in pytest temporary path fixture.

    Returns:
        A `Path` object pointing to the created sandbox directory.

    Side Effects:
        Creates a physical directory on disk that Pytest will clean up later.

    Failure Behavior:
        None.
    """
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    return sandbox


@pytest.fixture
def mock_users_file(tmp_path: Path) -> Path:
    """
    Provides a temporary path for a mock users.json file.

    Args:
        tmp_path: The built-in pytest temporary path fixture.

    Returns:
        A `Path` object pointing to where the JSON should be written.

    Side Effects:
        None (it just yields the path).

    Failure Behavior:
        None.
    """
    users_file = tmp_path / "users.json"
    return users_file


@pytest.fixture
def server_backend(tmp_sandbox, mock_users_file):
    """
    Spawns a real ServerBackend bound to an ephemeral localhost port.

    Args:
        tmp_sandbox: The fixture providing the test directory.
        mock_users_file: The fixture providing the test credentials file.

    Returns:
        A running `ServerBackend` instance.

    Side Effects:
        Binds a real TCP socket to `127.0.0.1:0`.
        Spawns background network threads.
        Writes a "testuser" credential to the mock file.

    Failure Behavior:
        If the server fails to bind after 50 retries, it yields a broken server.
    """
    auth = AuthManager(mock_users_file)
    # Seed a known test user
    auth.add_user("testuser", "testpass")

    files = FileManager(tmp_sandbox)
    server = ServerBackend(auth, files)

    # Bind to port 0 to let OS pick a free port, preventing collisions
    server.start("127.0.0.1", 0)

    # Wait for socket to be ready
    for _ in range(50):
        if server.is_running and server.engine._socket:
            break
        time.sleep(0.01)

    yield server
    server.stop()


@pytest.fixture
def client_backend(qtbot):
    """
    Provides an unconnected ClientBackend instance.

    Args:
        qtbot: The pytest-qt fixture for GUI event loop management.

    Returns:
        A clean `ClientBackend` instance.

    Side Effects:
        Yields the client for the test.
        Automatically calls `disconnect()` during fixture teardown.

    Failure Behavior:
        None.
    """
    client = ClientBackend()
    yield client
    if client.is_connected:
        client.disconnect()
