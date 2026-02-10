"""
Logger Utilities
────────────────
Provides a simple, consistent logging setup for both client and server.
Logs are written to rotating daily files **and** the console.
"""

import logging
from datetime import datetime
from pathlib import Path


def setup_logger(
    name: str,
    log_dir: str | Path | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Create and configure a logger.

    Args:
        name:    Logger name (``"server"`` or ``"client"``).
        log_dir: Directory for log files.  Console-only if *None*.
        level:   Minimum logging level (default ``INFO``).

    Returns:
        A ready-to-use :class:`logging.Logger`.
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
