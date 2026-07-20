"""
Module: file_ops.py
───────────────────
Purpose: Executes rapid, synchronous filesystem operations (LIST, MKDIR, DELETE).

Architectural Role:
Acts as the execution handler for synchronous file management commands. It bridges 
the network protocol layer with the secure sandbox layer provided by `FileManager`.

Responsibilities:
- Parse command arguments from the protocol payload list.
- Invoke the appropriate `FileManager` method (which handles path sandboxing).
- Format and emit protocol responses back to the client.

Expected Collaborators:
- `src.network.server.dispatcher` (invokes these methods).
- `src.storage.file_manager.FileManager` (executes the disk operations).
"""

import logging
from src.core.protocol import (
    CODE_ACTION_OK,
    CODE_BAD_REQ,
    CODE_FORBIDDEN,
    CODE_NOT_FOUND,
    CODE_OK,
    ProtocolHandler,
    STATUS_ERROR,
    STATUS_OK,
)
from src.storage.file_manager import FileManager

logger = logging.getLogger("server.file_ops")

class FileOpsHandler:
    """
    Groups handlers for short-lived, synchronous filesystem commands.

    Why it exists:
    By grouping non-streaming commands together, we avoid polluting the transfer 
    handlers with simple tasks like renaming a file. This class expects all of its 
    operations to return immediately.

    Responsibilities:
    - Serializing the directory list into a string delimited by semi-colons.
    - Returning appropriate error codes (e.g., CODE_NOT_FOUND) when disk operations fail.

    Non-Responsibilities (Anti-Goals):
    - It does NOT perform byte streaming for uploads/downloads.
    - It does NOT perform path sanitization (delegated entirely to `FileManager`).
    """

    def __init__(self, file_manager: FileManager):
        self.files = file_manager

    def cmd_list(self, proto: ProtocolHandler, parts: list, user: str, engine):
        """
        Retrieves a directory listing and serializes it for the client.

        Args:
            proto: The client's protocol handler.
            parts: The parsed command payload.
            user: The authenticated username.
            engine: The parent server engine.

        Returns:
            None.

        Side Effects:
            Sends a formatted string over the socket.

        Failure Behavior:
            Sends `CODE_NOT_FOUND` if the path doesn't exist or escapes the sandbox.
        """
        path = parts[1] if len(parts) > 1 else ""
        entries = self.files.list_directory(user, path)
        if entries is None:
            proto.send_message(CODE_NOT_FOUND, STATUS_ERROR, "Invalid path")
            return

        formatted = []
        for e in entries:
            formatted.append(f"{e['name']}:{e['size']}:{e['type']}")
        payload = ";".join(formatted)

        proto.send_message(CODE_OK, STATUS_OK, payload)

    def cmd_mkdir(self, proto: ProtocolHandler, parts: list, user: str, engine):
        """
        Creates a new directory within the user's sandbox.

        Args:
            proto: The client's protocol handler.
            parts: The parsed command payload.
            user: The authenticated username.
            engine: The parent server engine.

        Returns:
            None.

        Side Effects:
            Mutates the filesystem (creates a folder).
            Sends a protocol response over the socket.

        Failure Behavior:
            Sends an error code if the arguments are missing or creation fails.
        """
        if len(parts) < 2:
            proto.send_message(CODE_BAD_REQ, STATUS_ERROR, "Missing dirname")
            return
        dirname = parts[1]
        if self.files.create_directory(user, dirname):
            proto.send_message(CODE_ACTION_OK, STATUS_OK, "Directory created")
            engine.on_log_message(f"'{user}' created dir: {dirname}")
        else:
            proto.send_message(CODE_FORBIDDEN, STATUS_ERROR, "Could not create directory")

    def cmd_delete(self, proto: ProtocolHandler, parts: list, user: str, engine):
        """
        Deletes a file or directory.

        Args:
            proto: The client's protocol handler.
            parts: The parsed command payload.
            user: The authenticated username.
            engine: The parent server engine.

        Returns:
            None.

        Side Effects:
            Mutates the filesystem (deletes an item).
            Sends a protocol response over the socket.

        Failure Behavior:
            Sends `CODE_FORBIDDEN` if the deletion is blocked.
        """
        if len(parts) < 2:
            proto.send_message(CODE_BAD_REQ, STATUS_ERROR, "Missing filename")
            return
        filename = parts[1]
        
        if self.files.delete(user, filename):
            proto.send_message(CODE_ACTION_OK, STATUS_OK, "Deleted")
        else:
            proto.send_message(CODE_FORBIDDEN, STATUS_ERROR, "Failed to delete file")

    def cmd_rename(self, proto: ProtocolHandler, parts: list, user: str, engine):
        """
        Renames a file or directory.

        Args:
            proto: The client's protocol handler.
            parts: The parsed command payload.
            user: The authenticated username.
            engine: The parent server engine.

        Returns:
            None.

        Side Effects:
            Mutates the filesystem (renames an item).
            Sends a protocol response over the socket.

        Failure Behavior:
            Sends `CODE_FORBIDDEN` if the rename is blocked or invalid.
        """
        if len(parts) < 3:
            proto.send_message(CODE_BAD_REQ, STATUS_ERROR, "Missing arguments")
            return
        old_name, new_name = parts[1], parts[2]
        
        if self.files.rename(user, old_name, new_name):
            proto.send_message(CODE_ACTION_OK, STATUS_OK, "Renamed")
        else:
            proto.send_message(CODE_FORBIDDEN, STATUS_ERROR, "Failed to rename file")

    def cmd_move(self, proto: ProtocolHandler, parts: list, user: str, engine):
        """
        Moves a file into a different directory.

        Args:
            proto: The client's protocol handler.
            parts: The parsed command payload.
            user: The authenticated username.
            engine: The parent server engine.

        Returns:
            None.

        Side Effects:
            Mutates the filesystem (moves an item).
            Sends a protocol response over the socket.

        Failure Behavior:
            Sends `CODE_FORBIDDEN` if the move is blocked or invalid.
        """
        if len(parts) < 3:
            proto.send_message(CODE_BAD_REQ, STATUS_ERROR, "Missing arguments")
            return
        filename, dest_dir = parts[1], parts[2]
        
        if self.files.move(user, filename, dest_dir):
            proto.send_message(CODE_ACTION_OK, STATUS_OK, "Moved")
        else:
            proto.send_message(CODE_FORBIDDEN, STATUS_ERROR, "Failed to move file")
