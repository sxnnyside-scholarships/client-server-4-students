"""
File Manager
────────────
Manages the server's per-user file storage.

Every authenticated user gets their own **sandbox** directory.
All path operations are validated to prevent directory-traversal attacks.
"""

from pathlib import Path


class FileManager:
    """Per-user sandboxed file storage."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # ── path helpers ──────────────────────────────────────────

    def get_user_dir(self, username: str) -> Path:
        """Return (and create) the user's home directory."""
        user_dir = self.base_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def resolve_path(self, username: str, relative_path: str = "") -> Path | None:
        """Safely resolve *relative_path* inside the user sandbox.

        Returns ``None`` if the resolved path would escape the sandbox
        (i.e., a directory-traversal attempt with ``..``).
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
        """List the contents of a directory inside the user sandbox.

        Returns a list of dicts ``{"name", "size", "type"}``
        or ``None`` on invalid path.
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
        """Check whether a file exists in the user sandbox."""
        target = self.resolve_path(username, relative_path)
        return target is not None and target.is_file()

    def get_file_size(self, username: str, relative_path: str) -> int | None:
        """Return file size in bytes, or ``None`` if not found."""
        target = self.resolve_path(username, relative_path)
        if target is None or not target.is_file():
            return None
        return target.stat().st_size

    def get_file_path(self, username: str, relative_path: str) -> Path | None:
        """Return the absolute path to a file for direct I/O."""
        return self.resolve_path(username, relative_path)

    def create_directory(self, username: str, relative_path: str) -> bool:
        """Create a directory inside the user sandbox."""
        target = self.resolve_path(username, relative_path)
        if target is None:
            return False
        try:
            target.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False
