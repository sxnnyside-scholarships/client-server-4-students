"""
Package: src.network.client
───────────────────────────
Purpose: Encapsulates the multi-threaded networking engines specifically required for the Client application.

Architectural Role:
Decomposes the massive client networking workload into cohesive, single-responsibility 
engines. This sub-package sits beneath `ClientBackend` (which acts as a unified facade).

Responsibilities:
- Manage outbound TCP socket connections and handshakes (`engine.py`).
- Execute synchronous, fast command-response pairs like LIST and MKDIR (`operations.py`).
- Safely stream large files asynchronously without blocking the main socket loop (`transfers.py`).

Public API:
- `engine.ClientConnectionEngine`: Socket and thread lifecycle manager.
- `operations.ClientOperations`: Non-blocking fast command executor.
- `transfers.ClientTransferEngine`: File upload/download byte streaming logic.

Expected Collaborators:
- `src.network.client_backend`: Acts as the parent Facade, wrapping these engines in PyQt signals.
"""
