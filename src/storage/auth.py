"""
Module: auth.py
───────────────
Purpose: Handles user credentials, password hashing, and storage.

Architectural Role:
Acts as the identity provider for the server. It decouples the network handlers
from the underlying credential storage format, allowing the server to authenticate
connections dynamically.

Responsibilities:
- Hash plaintext passwords securely using SHA-256 and per-user salts.
- Persist credential hashes to a JSON file.
- Verify inbound authentication requests.

Expected Collaborators:
- `src.network.server.handlers.auth` (consumes `verify`)
- `src.ui.server_window` (consumes user management methods)

# Important Implementation Notes:
# Educational Note: Hashing Algorithms
# This implementation has been modernized to use `bcrypt`. Bcrypt is a secure
# password hashing function that automatically incorporates salting and a
# configurable work factor (rounds). This makes it resistant to brute-force
# and rainbow table attacks, unlike the legacy SHA-256 implementation.
"""

import hashlib
import json
import bcrypt
from pathlib import Path

from src.network.security import is_valid_username


class AuthManager:
    """
    JSON-file-backed user authentication store.

    Why it exists:
    Provides a persistent identity registry so that students do not have to
    re-create accounts every time they restart the server.

    Responsibilities:
    - Verifying usernames and passwords against stored hashes.
    - Providing CRUD operations for user accounts.

    Non-Responsibilities (Anti-Goals):
    - It does NOT authorize file access (delegated to `FileManager`).
    - It does NOT enforce rate-limiting (delegated to `SecurityContext`).
    """

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
    def _hash_password(password: str) -> tuple[str, str]:
        """Return ``(bcrypt_hash, "bcrypt")`` for *password*."""
        import sys

        rounds = 4 if "pytest" in sys.modules else 12
        salt = bcrypt.gensalt(rounds=rounds)
        digest = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        return digest, "bcrypt"

    @staticmethod
    def _legacy_hash_password(password: str, salt: str) -> tuple[str, str]:
        """Legacy SHA-256 hashing for backward compatibility."""
        digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return digest, salt

    # ── public API ────────────────────────────────────────────

    def verify(self, username: str, password: str) -> bool:
        """
        Validates a plaintext password against the stored hash for a given user.

        Args:
            username: The account name to verify.
            password: The plaintext password provided by the client.

        Returns:
            True if the credentials match, False otherwise.

        Side Effects:
            None.

        Failure Behavior:
            Returns False if the username does not exist.
        """
        if username not in self.users:
            return False
        stored = self.users[username]
        stored_hash = stored["hash"]
        stored_salt = stored.get("salt", "")

        if stored_salt == "bcrypt":
            # Modern bcrypt verification
            try:
                return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
            except ValueError:
                return False
        else:
            # Legacy SHA-256 fallback
            digest, _ = self._legacy_hash_password(password, stored_salt)
            if digest == stored_hash:
                # Educational Note: Automatic Migration
                # Transparently upgrade the user to a modern bcrypt hash upon successful login.
                new_digest, new_indicator = self._hash_password(password)
                self.users[username] = {"hash": new_digest, "salt": new_indicator}
                self._save()
                return True
            return False

    def add_user(self, username: str, password: str) -> bool:
        """
        Creates a new user account with a salted password hash.

        Args:
            username: The desired username (must pass validation).
            password: The plaintext password to hash and store.

        Returns:
            True if the user was successfully created, False otherwise.

        Side Effects:
            Mutates the internal user dictionary.
            Writes the updated dictionary to the JSON file on disk.

        Failure Behavior:
            Returns False if the username contains illegal characters (e.g., path traversal markers).
            Returns False if the username already exists.
        """
        if not is_valid_username(username):
            return False
        if username in self.users:
            return False
        digest, salt = self._hash_password(password)
        self.users[username] = {"hash": digest, "salt": salt}
        self._save()
        return True

    def remove_user(self, username: str) -> bool:
        """
        Deletes a user account from the registry.

        Args:
            username: The account to delete.

        Returns:
            True if the user was deleted, False if they did not exist.

        Side Effects:
            Mutates the internal user dictionary.
            Writes the updated dictionary to the JSON file on disk.

        Failure Behavior:
            Returns False if the username is not found.
        """
        if username not in self.users:
            return False
        del self.users[username]
        self._save()
        return True

    def list_users(self) -> list[str]:
        """
        Retrieves a list of all registered usernames.

        Args:
            None.

        Returns:
            A list of string usernames.

        Side Effects:
            None.

        Failure Behavior:
            None.
        """
        return list(self.users.keys())

    def change_password(self, username: str, new_password: str) -> bool:
        """
        Updates the password for an existing user account.

        Args:
            username: The account to modify.
            new_password: The new plaintext password.

        Returns:
            True if the password was updated, False otherwise.

        Side Effects:
            Generates a new cryptographic salt.
            Mutates the internal user dictionary.
            Writes the updated dictionary to the JSON file on disk.

        Failure Behavior:
            Returns False if the user does not exist.
        """
        if username not in self.users:
            return False
        digest, salt = self._hash_password(new_password)
        self.users[username] = {"hash": digest, "salt": salt}
        self._save()
        return True
