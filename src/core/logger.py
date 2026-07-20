"""
Module: logger.py
─────────────────
Purpose: Provides a simple, consistent logging setup for both the client and server.

Architectural Role:
Standardizes telemetry and debugging output across the application. By centralizing 
logger creation, it ensures that logs are uniformly formatted and safely rotated.

Responsibilities:
- Create Python standard library `logging.Logger` instances.
- Attach console and daily-rotating file handlers.
- Prevent duplicate handler registration.

Expected Collaborators:
- Virtually every file in the repository (calls `setup_logger`).
- `src.core.runtime` (provides the directory path for log files).

Important Implementation Notes:
It is safe to call `setup_logger` multiple times for the same module name; it detects 
existing handlers and avoids duplicating output streams.
"""

import logging
from datetime import datetime
from pathlib import Path


def setup_logger(
    name: str,
    log_dir: str | Path | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Creates and configures a standardized logger instance.

    Args:
        name: The string identifier for the logger (e.g., "server" or "client").
        log_dir: The directory where log files should be written. If None, 
                 only console logging is enabled.
        level: The minimum severity level to log (defaults to logging.INFO).

    Returns:
        A fully configured `logging.Logger` instance.

    Side Effects:
        Creates a new log file on the disk if `log_dir` is provided.
        Modifies the global state of the Python `logging` module.

    Failure Behavior:
        Raises `OSError` if the `log_dir` cannot be created due to permissions.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers when called more than once
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler — always present
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler — optional
    if log_dir is not None:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        file_handler = logging.FileHandler(
            log_path / f"{name}_{timestamp}.log",
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
