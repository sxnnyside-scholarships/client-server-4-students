"""
Package: src.network.server.handlers
────────────────────────────────────
Purpose: Contains the specific execution logic for every supported CS4S protocol command.

Architectural Role:
Acts as the execution leaf-nodes of the server architecture. These handlers are dynamically
registered with the `CommandDispatcher`. They decouple the *parsing and routing* of a network
request from the *actual execution* of the file/auth operation.

Responsibilities:
- Execute Authentication commands (`auth.py`).
- Execute standard File Operations like LIST, MKDIR, DELETE (`file_ops.py`).
- Execute long-running byte streams for UPLOAD and DOWNLOAD (`transfer.py`).

Public API:
- `auth.AuthCommandHandler`: Logic for `CMD_AUTH`.
- `file_ops.FileOpsHandler`: Logic for rapid synchronous filesystem modifications.
- `transfer.TransferHandler`: Logic for reading/writing raw byte streams over the socket.

Expected Collaborators:
- `src.storage`: Consumed by these handlers to mutate the virtual filesystem and verify credentials.
"""
