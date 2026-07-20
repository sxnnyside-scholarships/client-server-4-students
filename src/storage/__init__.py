"""
Package: src.storage
────────────────────
Purpose: Manages persistent data storage, including user authentication credentials and the sandboxed virtual filesystem.

Architectural Role:
Acts as the persistent data layer. It abstracts the host operating system's filesystem 
and provides a secure, sandboxed interface for the network layer to read/write data without 
risking path traversal or unauthorized access.

Responsibilities:
- Validate, hash, and persist user credentials (`auth.py`).
- Isolate file operations within per-user sandbox boundaries (`file_manager.py`).

Public API:
- `auth.AuthManager`: Handles user verification and password hashing.
- `file_manager.FileManager`: Handles sandboxed file enumeration, uploads, downloads, and deletions.

Expected Collaborators:
- `src.network.server`: Consumes `AuthManager` to validate connecting clients.
- `src.network.server`: Consumes `FileManager` to execute incoming FTP-style commands safely.
"""
