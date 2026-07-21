# CS4S Developer Guide

Welcome to the Client-Server 4 Students (CS4S) repository! This guide explains how to extend, test, and package the application.

## 1. Repository Organization

CS4S separates concerns clearly into distinct modules:

- **`src/core/`**: Shared utilities like `config.py` and `protocol.py`. Both the client and server depend on these.
- **`src/network/client/`**: The client-side connection manager and socket background threads.
- **`src/network/server/`**: The server-side multi-threaded TCP engine and command dispatchers.
- **`src/storage/`**: Disk-bound utilities for authenticating users (`auth.py`) and managing the sandbox (`file_manager.py`).
- **`src/ui/`**: PyQt6 GUI components. Avoid putting business logic in these files!
- **`tests/`**: Unit and integration test suites using `pytest`.

## 2. Engineering Workflow

We use **Poetry** to maintain deterministic environments.

### Environment Setup
```bash
# Install dependencies
poetry install

# Run the application
poetry run python main.py
```

### Static Analysis
Before submitting a pull request, ensure the codebase passes our automated quality checks:
```bash
# Code Formatting & Linting (Ruff)
poetry run ruff check .

# Type Checking (MyPy)
poetry run mypy src/ tests/
```

### Testing
We enforce stateless testing. Do not rely on hardcoded paths or external network access.
```bash
poetry run pytest tests/
```

- **Unit tests** validate logic in isolation (e.g., `test_auth.py`).
- **Integration tests** spin up ephemeral localhost servers and validate complete socket streams (e.g., `test_protocol.py`).

## 3. Extending the Protocol

If you want to add a new protocol command (e.g., `COMPRESS`), you must modify the codebase in three places:

1. **Protocol Definition**: Add the command constant in `src/core/protocol.py`.
2. **Server Dispatcher**: Implement the logic in `src/network/server/handlers/` and map it in `src/network/server/dispatcher.py`.
3. **Client Operations**: Expose the command via `src/network/client/operations.py` so the GUI can trigger it.

Always update `docs/PROTOCOL_SPECIFICATION.md` when altering the protocol.

## 4. Packaging and Distribution

CS4S includes a robust distribution script utilizing PyInstaller to bundle PyQt6 and application assets.

```bash
# Generate native executable
poetry run python scripts/build_dist.py
```
This generates a portable application in the `dist/` directory suitable for Windows, macOS, or Linux depending on the host OS.
