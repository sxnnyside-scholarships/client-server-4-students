import csv
from pathlib import Path
from unittest.mock import MagicMock
from src.network.server.dispatcher import CommandDispatcher
from src.network.server.engine import ServerNetworkEngine
from src.storage.auth import AuthManager


def test_server_broadcast_message():
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
