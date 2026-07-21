"""
Package: src
────────────
Purpose: Root source package for the Client-Server 4 Students (CS4S) educational application.

Architectural Role:
Serves as the top-level namespace container for all application logic, isolating the
execution code from tests, build artifacts, and documentation.

Responsibilities:
- Provide a unified namespace (`src.`) for all internal imports.
- Enforce the boundary between production application code and external tooling.

Public API:
- None. This is a structural container.

Expected Collaborators:
- `tests/`: Consumes the `src` package to execute integration and unit tests.
- `main.py`: Consumes `src.ui.launcher` to bootstrap the application.
"""
