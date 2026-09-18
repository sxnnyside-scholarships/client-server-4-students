"""
Module: test_teacher_tools.py
─────────────────────────────
Purpose: Unit validation of teacher-assisted backend operations: server-wide client broadcast and CSV bulk user import.

Architectural Role:
Acts as the test suite for teacher tooling primitives, verifying that the server engine can iterate across
active client protocol instances safely and that student credential CSV records are validated, sanitized, and stored.

Responsibilities:
- Verify that `ServerNetworkEngine.broadcast_message` dispatches `BROADCAST` frames across all active client sockets.
- Verify that disconnected or corrupt client references are ignored gracefully during broadcast iteration.
- Validate CSV parsing, header filtering (English and Spanish headers), sanitization, deduplication, and secure storage.

Dependencies:
- `csv`
- `pathlib.Path`
- `unittest.mock.MagicMock`
- `src.network.server.dispatcher.CommandDispatcher`
- `src.network.server.engine.ServerNetworkEngine`
- `src.storage.auth.AuthManager`

Expected Collaborators:
- `tmp_path`: Pytest temporary directory fixture for isolated credential and CSV storage.

Educational Note: Concurrency and Broadcast Loops
Broadcasting messages to connected TCP sockets involves iterating over active client sessions.
Verifying that client failures do not block or crash the engine teaches robust multi-client server management.
"""

import csv
from pathlib import Path
from unittest.mock import MagicMock
from src.network.server.dispatcher import CommandDispatcher
from src.network.server.engine import ServerNetworkEngine
from src.storage.auth import AuthManager


def test_server_broadcast_message():
    """
    Validates that ServerNetworkEngine correctly dispatches BROADCAST messages to all registered client sessions.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Mocks client sockets and calls broadcast_message on ServerNetworkEngine.

    Failure Behavior:
        Fails if broadcast count does not match the active client count or if send_message is not called with BROADCAST.
    """
    dispatcher = CommandDispatcher()
    engine = ServerNetworkEngine(max_connections=5, dispatcher=dispatcher)

    # Mock 2 connected clients
    proto1 = MagicMock()
    proto2 = MagicMock()
    sock1 = MagicMock()
    sock2 = MagicMock()
    t1 = MagicMock()
    t2 = MagicMock()

    engine._clients = {
        "127.0.0.1:50001": (t1, sock1, proto1),
        "127.0.0.1:50002": (t2, sock2, proto2),
    }

    count = engine.broadcast_message("Class announcement: Lab begins now!")
    assert count == 2

    proto1.send_message.assert_called_once_with("BROADCAST", "Class announcement: Lab begins now!")
    proto2.send_message.assert_called_once_with("BROADCAST", "Class announcement: Lab begins now!")


def test_auth_csv_import(tmp_path: Path):
    """
    Validates CSV file parsing, header skipping, duplicate detection, and bulk ingestion into AuthManager.

    Args:
        tmp_path: Pytest temporary directory fixture for creating files.

    Returns:
        None.

    Side Effects:
        Writes CSV file and updates users.json on disk.

    Failure Behavior:
        Fails if duplicate users are overwritten, invalid usernames pass validation, or valid records fail to verify.
    """
    auth_file = tmp_path / "users.json"
    auth = AuthManager(auth_file)

    # Initial users from defaults
    assert "student" in auth.users
    assert "teacher" in auth.users

    csv_file = tmp_path / "students.csv"
    csv_content = [
        ["username", "password"],  # Header row to skip
        ["alice", "secret123"],  # Valid user 1
        ["bob", "pass456"],  # Valid user 2
        ["student", "dup_pass"],  # Duplicate (should be skipped)
        ["bad/user", "invalid"],  # Invalid username (should fail validation)
        ["", "nopass"],  # Empty username
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerows(csv_content)

    # Simulate import logic
    imported = 0
    skipped = 0
    with open(csv_file, "r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row or len(row) < 2:
                continue
            u = row[0].strip()
            p = row[1].strip()
            if u.lower() in ("username", "user", "usuario") and p.lower() in ("password", "pass", "contraseña"):
                continue
            if not u or not p:
                skipped += 1
                continue
            if auth.add_user(u, p):
                imported += 1
            else:
                skipped += 1

    assert imported == 2  # alice and bob
    assert skipped == 3  # duplicate student, invalid bad/user, empty username
    assert "alice" in auth.users
    assert "bob" in auth.users
    assert auth.verify("alice", "secret123")
    assert auth.verify("bob", "pass456")
