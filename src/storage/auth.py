"""
Authentication Manager
──────────────────────
Handles user credentials: hashing, storage, and verification.

Passwords are hashed with **SHA-256 + per-user random salt**.

.. warning::

   This is intentionally simple for educational purposes.
   A production system should use *bcrypt* or *argon2*.
"""

import hashlib
import json
import secrets
from pathlib import Path


class AuthManager:
    """JSON-file-backed user authentication store."""

    def __init__(self, users_file: str | Path):
        self.path = Path(users_file)
        self.users: dict[str, dict] = {}
        self._load()

    # ── persistence ───────────────────────────────────────────

    def _load(self):
        """Load users from disk, or create defaults on first run."""
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    self.users = json.load(fh)
                return
            except (json.JSONDecodeError, IOError):
                pass
        self._create_defaults()

    def _create_defaults(self):
        """Seed the store with two demo accounts so the project works
        straight out of the box."""
        self.users = {}
        self.add_user("student", "student")
        self.add_user("teacher", "teacher")

    def _save(self):
        """Write the current user database to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.users, fh, indent=4, ensure_ascii=False)

    # ── hashing helpers ───────────────────────────────────────

    @staticmethod
    def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
        """Return ``(hex_digest, salt)`` for *password*."""
        if salt is None:
            salt = secrets.token_hex(16)
        digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return digest, salt

    # ── public API ────────────────────────────────────────────

    def verify(self, username: str, password: str) -> bool:
        """Return *True* if the credentials are valid."""
        if username not in self.users:
            return False
        stored = self.users[username]
        digest, _ = self._hash_password(password, stored["salt"])
        return digest == stored["hash"]

    def add_user(self, username: str, password: str) -> bool:
        """Add a new user.  Returns *False* if the name is taken."""
        if username in self.users:
            return False
        digest, salt = self._hash_password(password)
        self.users[username] = {"hash": digest, "salt": salt}
        self._save()
        return True

    def remove_user(self, username: str) -> bool:
        """Remove a user.  Returns *False* if not found."""
        if username not in self.users:
            return False
        del self.users[username]
        self._save()
        return True

    def list_users(self) -> list[str]:
        """Return all registered usernames."""
        return list(self.users.keys())

    def change_password(self, username: str, new_password: str) -> bool:
        """Change a user's password.  Returns *False* if user unknown."""
        if username not in self.users:
            return False
        digest, salt = self._hash_password(new_password)
        self.users[username] = {"hash": digest, "salt": salt}
        self._save()
        return True
