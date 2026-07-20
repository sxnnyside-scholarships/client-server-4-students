"""
Package: src.network.server
───────────────────────────
Purpose: Encapsulates the multi-threaded networking engines specifically required for the Server application.

Architectural Role:
Decomposes the massive server networking workload into highly cohesive components. 
It cleanly separates the physical TCP socket loop (`engine.py`) from the logical 
command routing (`dispatcher.py`) and connection state (`connection.py`).

Responsibilities:
- Manage the listening socket and spawn per-client worker threads (`engine.py`).
- Maintain an active registry of connected clients.
- Route incoming string commands to designated handler functions (`dispatcher.py`).

Public API:
- `engine.ServerNetworkEngine`: Core lifecycle manager for the server sockets.
- `dispatcher.CommandDispatcher`: Routes commands securely.
- `connection.ClientConnectionHandler`: Runs the isolated read-loop for a single connected client.

Expected Collaborators:
- `src.network.server_backend`: The parent Facade wrapping these classes with PyQt signals.
- `src.network.server.handlers`: Consumed by the dispatcher to actually execute the routed commands.
"""
