"""
Module: errors.py
─────────────────
Purpose: Standardized networking error hierarchy and codes.

Architectural Role:
Acts as an abstraction layer between low-level OS networking code and the application GUI. 
It translates raw Python socket exceptions into localized, meaningful Enum values that 
the frontend can safely display to students without leaking stack traces.

Responsibilities:
- Define the `NetworkError` enumeration.
- Provide the `map_socket_error` translation function.

Expected Collaborators:
- `src.network.client.engine`
- `src.network.server.engine`
"""

from enum import Enum


class NetworkError(Enum):
    """
    Standardized error categories for client-server communication.

    Why it exists:
    Because `ConnectionResetError` and `ConnectionAbortedError` mean the same thing 
    to an end user: the connection was lost. This Enum simplifies error handling 
    for the GUI components.

    Responsibilities:
    - Grouping similar network failures under semantic definitions.

    Non-Responsibilities (Anti-Goals):
    - It does NOT contain language-specific translations (handled by LocaleManager).
    """
    SERVER_UNAVAILABLE = "ServerUnavailable"
    """The server is offline or unreachable."""
    
    CONNECTION_REFUSED = "ConnectionRefused"
    """The server actively refused the connection (port closed)."""
    
    AUTH_FAILED = "AuthFailed"
    """The provided credentials were rejected."""
    
    CONNECTION_LOST = "ConnectionLost"
    """The active connection was abruptly terminated."""
    
    TIMEOUT = "Timeout"
    """A network operation exceeded the maximum allowed time."""
    
    PROTOCOL_ERROR = "ProtocolError"
    """The remote peer violated the communication protocol."""
    
    INTERNAL_ERROR = "InternalError"
    """An unexpected local error occurred."""


def map_socket_error(exc: Exception) -> NetworkError:
    """
    Maps a raw Python socket/OS exception to a standardized NetworkError.

    Args:
        exc: The caught Python exception instance.

    Returns:
        The corresponding `NetworkError` enum value.

    Side Effects:
        None.

    Failure Behavior:
        If the exception is unknown, it defaults to `NetworkError.INTERNAL_ERROR`.
    """
    if isinstance(exc, ConnectionRefusedError):
        return NetworkError.CONNECTION_REFUSED
    elif type(exc).__name__ == 'timeout' or isinstance(exc, TimeoutError):
        return NetworkError.TIMEOUT
    elif isinstance(exc, ConnectionAbortedError):
        return NetworkError.CONNECTION_LOST
    elif isinstance(exc, ConnectionResetError):
        return NetworkError.CONNECTION_LOST
    elif isinstance(exc, ConnectionError):
        return NetworkError.CONNECTION_LOST
    return NetworkError.INTERNAL_ERROR
