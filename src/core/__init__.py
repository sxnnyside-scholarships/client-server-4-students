"""
Package: src.core
─────────────────
Purpose: Provides foundational utilities, configuration management, and protocol definitions shared across the entire application.

Architectural Role:
Acts as the central dependency for all other packages. It contains no business logic
or UI components, ensuring that high-level modules can depend on it without risking
circular dependencies.

Responsibilities:
- Define the byte-level and string-level network protocol (`protocol.py`).
- Manage application-wide settings and JSON configuration persistence (`config.py`).
- Provide cross-platform filesystem path resolution (`runtime.py`).
- Standardize logging behavior and file rotation (`logger.py`).

Public API:
- `config.ConfigManager`: Persists and retrieves application settings.
- `logger.setup_logger`: Configures rotating file loggers.
- `protocol.ProtocolHandler`: Low-level TCP socket wrapper for sending/receiving framed messages.
- `runtime.RuntimeEnvironment`: Resolves OS-specific application data paths.

Expected Collaborators:
- `src.network`: Consumes `protocol.py` for client/server communication.
- `src.ui`: Consumes `config.py` and `runtime.py` to restore visual state and locale preferences.
- `src.storage`: Consumes `runtime.py` to determine where to safely store user sandboxes.
"""
