"""
Module: file_manager.py
───────────────────────
Purpose: Manages the server's per-user file storage and sandboxing.

Architectural Role:
Acts as the secure boundary between the host operating system's filesystem and the
remote FTP-style commands coming from the network layer.

Responsibilities:
- Create isolated sandbox directories for each authenticated user.
- Enforce strict path resolution to prevent directory-traversal (`../`) attacks.
- Execute all local filesystem I/O safely (list, rename, move, delete).

Expected Collaborators:
- `src.network.server.handlers.file_ops` (consumes synchronous I/O operations).
- `src.network.server.handlers.transfer` (consumes `get_file_path` for streaming bytes).
"""

from pathlib import Path


class FileManager:
    """
    Per-user sandboxed file storage engine.

    Why it exists:
    Network clients cannot be trusted to provide safe absolute file paths. This class
    exists to translate untrusted relative string paths into safe absolute OS paths,
    guaranteeing that clients cannot escape their designated storage folder.

    Responsibilities:
    - Normalizing relative paths against a designated `base_dir`.
    - Executing CRUD operations on the local disk.

    Non-Responsibilities (Anti-Goals):
    - It does NOT authenticate users (delegated to `AuthManager`).
    - It does NOT transmit file bytes over the network (delegated to Network Engine).
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # ── path helpers ──────────────────────────────────────────

    def get_user_dir(self, username: str) -> Path:
        """
        Retrieves the absolute path to a user's isolated sandbox folder.

        Args:
            username: The string identifier of the user.

        Returns:
            The absolute `pathlib.Path` to the user's sandbox directory.

        Side Effects:
            Creates the directory on the host disk if it does not already exist.

        Failure Behavior:
            Raises `OSError` if the host filesystem denies directory creation.
        """
        user_dir = self.base_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def resolve_path(self, username: str, relative_path: str = "") -> Path | None:
        """
        Safely resolves an untrusted relative path into an absolute OS path.

        # Educational Note: Path Traversal Protection
        # We prevent attacks like `../../../etc/passwd` by fully resolving the requested
        # path using `resolve()` (which eliminates `..`), and then using `relative_to()`
        # to strictly assert that the final path is a child of the intended user sandbox.

        Args:
            username: The user making the request.
            relative_path: The untrusted string path from the client.

        Returns:
            An absolute `pathlib.Path` if safe, or `None` if the path violates the sandbox.

        Side Effects:
            None.

        Failure Behavior:
            Returns `None` if the requested path attempts to traverse outside the sandbox.
        """
        user_dir = self.get_user_dir(username)
        try:
            full = (user_dir / relative_path).resolve()
        except (ValueError, OSError):
            return None

        # Security: ensure the path stays inside the sandbox
        try:
            full.relative_to(user_dir.resolve())
        except ValueError:
            return None
        return full

    # ── public API ────────────────────────────────────────────

    def list_directory(self, username: str, relative_path: str = "") -> list[dict] | None:
        """
        Returns the contents of a directory formatted for network transmission.

        Args:
            username: The user requesting the list.
            relative_path: The untrusted target directory path.

        Returns:
            A list of dictionaries containing 'name', 'size', and 'type', or `None`.

        Side Effects:
            Reads disk metadata. Skips hidden files (names starting with `.`).

        Failure Behavior:
            Returns `None` if the path is unsafe, missing, or throws `PermissionError`.
        """
        target = self.resolve_path(username, relative_path)
        if target is None or not target.is_dir():
            return None

        entries: list[dict] = []
        try:
            for item in sorted(target.iterdir()):
                if item.name.startswith("."):
                    continue
                entries.append(
                    {
                        "name": item.name,
                        "size": item.stat().st_size if item.is_file() else 0,
                        "type": "file" if item.is_file() else "dir",
                    }
                )
        except PermissionError:
            return None
        return entries

    def file_exists(self, username: str, relative_path: str) -> bool:
        """
        Verifies if a specific file exists within the user's sandbox.

        Args:
            username: The user.
            relative_path: The untrusted path to check.

        Returns:
            True if the path safely resolves and points to a file. False otherwise.

        Side Effects:
            None.

        Failure Behavior:
            Returns False for directories or invalid paths.
        """
        target = self.resolve_path(username, relative_path)
        return target is not None and target.is_file()

    def get_file_size(self, username: str, relative_path: str) -> int | None:
        """
        Retrieves the byte size of a file.

        Args:
            username: The user.
            relative_path: The untrusted file path.

        Returns:
            The size in bytes as an integer, or `None`.

        Side Effects:
            Reads disk metadata.

        Failure Behavior:
            Returns `None` if the path is unsafe or the file does not exist.
        """
        target = self.resolve_path(username, relative_path)
        if target is None or not target.is_file():
            return None
        return target.stat().st_size

    def get_file_path(self, username: str, relative_path: str) -> Path | None:
        """
        Provides the absolute path for raw byte streaming.

        Args:
            username: The user.
            relative_path: The untrusted file path.

        Returns:
            The absolute `pathlib.Path`, or `None` if unsafe.

        Side Effects:
            None.

        Failure Behavior:
            Returns `None` if the path violates sandbox rules.
        """
        return self.resolve_path(username, relative_path)

    def create_directory(self, username: str, relative_path: str) -> bool:
        """
        Creates a new folder inside the sandbox.

        Args:
            username: The user.
            relative_path: The desired folder name/path.

        Returns:
            True if created, False otherwise.

        Side Effects:
            Mutates the host filesystem.

        Failure Behavior:
            Returns False if the path is unsafe or an OS permission error occurs.
        """
        target = self.resolve_path(username, relative_path)
        if target is None:
            return False
        try:
            target.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False

    def delete(self, username: str, relative_path: str) -> bool:
        """
        Recursively deletes a file or folder from the sandbox.

        Args:
            username: The user.
            relative_path: The target to delete.

        Returns:
            True if deleted successfully, False otherwise.

        Side Effects:
            Destructively mutates the host filesystem.

        Failure Behavior:
            Returns False if the user attempts to delete the sandbox root (`.`).
            Returns False on missing files or OS permission errors.
        """
        if not relative_path or relative_path == ".":
            return False  # Prevent deleting the sandbox root

        target = self.resolve_path(username, relative_path)
        if target is None or not target.exists():
            return False

        try:
            if target.is_file():
                target.unlink()
            elif target.is_dir():
                import shutil

                shutil.rmtree(target)
            return True
        except OSError:
            return False

    def rename(self, username: str, old_rel: str, new_rel: str) -> bool:
        """
        Renames a file or folder within the sandbox.

        Args:
            username: The user.
            old_rel: The original path.
            new_rel: The desired new path.

        Returns:
            True if renamed, False otherwise.

        Side Effects:
            Mutates the host filesystem.

        Failure Behavior:
            Returns False if either path is unsafe, the old file is missing,
            or the new file already exists (preventing overwrites).
        """
        old_target = self.resolve_path(username, old_rel)
        new_target = self.resolve_path(username, new_rel)

        if old_target is None or new_target is None:
            return False
        if not old_target.exists() or new_target.exists():
            return False

        try:
            old_target.rename(new_target)
            return True
        except OSError:
            return False

    def move(self, username: str, rel_path: str, dest_dir_rel: str) -> bool:
        """
        Moves a file or folder into a destination folder inside the sandbox.

        Args:
            username: The user.
            rel_path: The target to move.
            dest_dir_rel: The destination directory.

        Returns:
            True if moved, False otherwise.

        Side Effects:
            Mutates the host filesystem. May create the destination directory if missing.

        Failure Behavior:
            Returns False if paths are unsafe, or if the client attempts a circular move
            (e.g., moving a folder inside of itself).
        """
        src_target = self.resolve_path(username, rel_path)
        if src_target is None or not src_target.exists():
            return False

        # The destination directory might not exist yet, but we must validate the path
        # by checking its parent or resolving it as if it exists.
        dest_dir_target = self.resolve_path(username, dest_dir_rel)
        if dest_dir_target is None:
            return False

        # Prevent circular moves (e.g. moving a folder into itself)
        if dest_dir_target.is_relative_to(src_target):
            return False

        dest_file_target = dest_dir_target / src_target.name
        if dest_file_target.exists():
            return False

        try:
            dest_dir_target.mkdir(parents=True, exist_ok=True)
            src_target.rename(dest_file_target)
            return True
        except OSError:
            return False
