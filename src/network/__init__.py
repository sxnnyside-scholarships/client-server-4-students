"""
Package: src.network
────────────────────
Purpose: Contains all client and server networking infrastructure, protocol parsing, and security validation logic.

Architectural Role:
This is the core execution engine of the application. It acts as the bridge between the
host OS's TCP sockets and the application's internal data structures. It strictly isolates
blocking I/O operations (like socket reads/writes) from the main GUI thread.

Responsibilities:
- Manage the raw TCP socket lifecycles for both the Client and Server.
- Enforce the CS4S protocol format.
- Maintain thread-safe state synchronization.
- Provide clean `QObject` signal/slot facades so the UI can observe network events without blocking.

Public API:
- `client_backend.ClientBackend`: The top-level facade for all client operations.
- `server_backend.ServerBackend`: The top-level facade for all server operations.
- `errors.NetworkError`: Standardized networking exceptions.
- `security.SecurityContext`: State tracker for rate-limiting and connection penalties.

Expected Collaborators:
- `src.ui`: Instantiates and listens to the backend facades.
- `src.storage`: The server backend consumes `AuthManager` and `FileManager` to execute incoming requests safely.
"""
