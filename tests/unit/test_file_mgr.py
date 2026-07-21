"""
Module: test_file_mgr.py
────────────────────────
Purpose: Validates the virtual filesystem boundary and path resolution security.

Architectural Role:
Unit testing for the `FileManager` component. Ensures that all low-level disk
modifications are bounded to the designated sandbox path.

Responsibilities:
- Verify path resolution blocks traversal attacks.
- Verify that directory listing parses and sorts correctly.
- Verify edge cases for move, rename, and delete commands.

Expected Collaborators:
- `pytest` (test runner).
- `src.storage.file_manager.FileManager` (the subject under test).
"""

from src.storage.file_manager import FileManager


def test_file_manager_sandbox_resolution(tmp_sandbox):
    """
    Validates path resolution and traversal protections.

    Args:
        tmp_sandbox: Pytest fixture providing a safe sandbox path.

    Returns:
        None.

    Side Effects:
        Writes directories to the temporary disk.

    Failure Behavior:
        Fails if malicious paths like `../../` resolve outside the sandbox instead of returning `None`.

    Ensure resolve_path correctly maps relative paths into the sandbox,
    and explicitly returns None when a path attempts to traverse out.
    """
    fm = FileManager(tmp_sandbox)

    # Create the user directory
    user_dir = fm.get_user_dir("student")
    assert user_dir.exists()
    assert user_dir == tmp_sandbox / "student"

    # Valid relative paths
    valid_file = fm.resolve_path("student", "test.txt")
    assert valid_file == user_dir / "test.txt"

    valid_nested = fm.resolve_path("student", "folder/test.txt")
    assert valid_nested == user_dir / "folder" / "test.txt"

    # Path Traversal attempts must return None
    assert fm.resolve_path("student", "../root.txt") is None
    assert fm.resolve_path("student", "../../etc/passwd") is None
    assert fm.resolve_path("student", "/absolute/path.txt") is None


def test_file_manager_directory_listing(tmp_sandbox):
    """
    Validates the structured output of directory listings.

    Args:
        tmp_sandbox: Pytest fixture providing a safe sandbox path.

    Returns:
        None.

    Side Effects:
        Writes dummy files to the temporary disk.

    Failure Behavior:
        Fails if file metadata (size, type) is calculated incorrectly or sorting is non-deterministic.

    Ensure listing a directory returns the expected dictionaries,
    and handles missing/invalid directories safely.
    """
    fm = FileManager(tmp_sandbox)
    user_dir = fm.get_user_dir("student")

    # Create some dummy files
    (user_dir / "file1.txt").write_text("hello")
    (user_dir / "folder").mkdir()

    entries = fm.list_directory("student", "")
    assert len(entries) == 2

    # Sort order is deterministic (file1.txt, folder)
    assert entries[0]["name"] == "file1.txt"
    assert entries[0]["type"] == "file"
    assert entries[0]["size"] == 5

    assert entries[1]["name"] == "folder"
    assert entries[1]["type"] == "dir"

    # Invalid directory returns None
    assert fm.list_directory("student", "does_not_exist") is None


def test_file_manager_mutations(tmp_sandbox):
    """
    Validates mutation operations (delete, rename, move).

    Args:
        tmp_sandbox: Pytest fixture providing a safe sandbox path.

    Returns:
        None.

    Side Effects:
        Mutates the filesystem aggressively within the sandbox.

    Failure Behavior:
        Fails if circular moves are permitted, or if root sandbox directories are deletable.

    Ensure delete, rename, and move operations function properly and
    respect the sandbox boundaries.
    """
    fm = FileManager(tmp_sandbox)
    user_dir = fm.get_user_dir("student")

    file_path = user_dir / "test.txt"
    file_path.write_text("dummy")

    # 1. Rename
    assert fm.rename("student", "test.txt", "new.txt") is True
    assert not file_path.exists()
    assert (user_dir / "new.txt").exists()

    # Rename conflict (destination exists)
    (user_dir / "other.txt").write_text("dummy")
    assert fm.rename("student", "new.txt", "other.txt") is False

    # 2. Move
    assert fm.move("student", "new.txt", "folder") is True
    assert not (user_dir / "new.txt").exists()
    assert (user_dir / "folder" / "new.txt").exists()

    # Circular move rejection
    assert fm.move("student", "folder", "folder/sub") is False

    # 3. Delete
    assert fm.delete("student", "folder/new.txt") is True
    assert not (user_dir / "folder" / "new.txt").exists()

    # Directory delete
    assert fm.delete("student", "folder") is True
    assert not (user_dir / "folder").exists()

    # Cannot delete sandbox root
    assert fm.delete("student", "") is False
    assert fm.delete("student", ".") is False
