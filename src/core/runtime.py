"""
Module: runtime.py
──────────────────
Purpose: Provides cross-platform path resolution for application data and configuration.

Architectural Role:
Acts as the filesystem boundary decider. It abstracts OS-specific differences
(Windows `APPDATA`, macOS `Library`, Linux `XDG_DATA_HOME`) so that the rest of
the application can request paths deterministically without writing OS checks.

Responsibilities:
- Resolve paths for logs, configurations, and user sandboxes.
- Detect "Portable Mode" execution (e.g., running from a USB drive).
- Automatically migrate legacy data folders from the project root into OS-compliant paths.

Expected Collaborators:
- `src.core.config` (uses paths to store settings)
- `src.core.logger` (uses paths to store logs)
- `src.storage.file_manager` (uses paths to construct sandboxes)

Important Implementation Notes:
The "Portable Mode" is activated simply by creating an empty `.portable` file
next to the executable. This overrides all OS-specific AppData resolution.
"""

import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger("core.runtime")


class RuntimeEnvironment:
    """
    Centralized resolution of application data paths.

    Why it exists:
    Hardcoding paths like `C:\\Users` or `~/.local` breaks cross-platform execution.
    This class ensures CS4S behaves like a well-behaved desktop application on every OS.

    Responsibilities:
    - Resolving absolute paths based on the `sys.platform`.
    - Bootstrapping the initial application directories.

    Non-Responsibilities (Anti-Goals):
    - It does NOT manage the contents of the files inside these directories.
    - It does NOT manage user authentication states.
    """

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self.data_dir = self._resolve_data_dir()

        self.config_dir = self.data_dir / "config"
        self.logs_dir = self.data_dir / "logs"
        self.sandboxes_dir = self.data_dir / "server_files"

        # Application assets bundled with the code
        self.locales_dir = self.project_root / "src" / "localization"
        self.themes_dir = self.project_root / "src" / "ui" / "themes"

    @property
    def is_portable(self) -> bool:
        """
        Determines whether the application is running in portable mode.

        Args:
            None.

        Returns:
            True if the `.portable` marker file is found in the project root, False otherwise.

        Side Effects:
            Reads from the filesystem to check file existence.

        Failure Behavior:
            Returns False if the filesystem read fails or file is missing.
        """
        return (self.project_root / ".portable").exists()

    def _resolve_data_dir(self) -> Path:
        if self.is_portable:
            return self.project_root / "runtime"

        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "CS4S"
            return Path.home() / "AppData" / "Roaming" / "CS4S"

        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "CS4S"

        else:
            # Linux/Unix
            xdg = os.environ.get("XDG_DATA_HOME")
            if xdg:
                return Path(xdg) / "CS4S"
            return Path.home() / ".local" / "share" / "CS4S"

    def bootstrap(self):
        """
        Prepares the runtime environment by ensuring required directories exist.

        # Educational Note: Migration Safeties
        # Migrating user data is dangerous. A crash midway through could lose files.
        # This implementation uses a "copy then rename-original" strategy to ensure
        # that if the migration fails, the original data is left untouched and unharmed.

        Args:
            None.

        Returns:
            None.

        Side Effects:
            Mutates the host filesystem by creating nested directories.
            May copy large amounts of data if a legacy migration triggers.

        Failure Behavior:
            Raises `RuntimeError` if directory creation fails (e.g., no permissions).
        """
        # 1. Migration
        if not self.is_portable:
            self._migrate_legacy_dir("config", self.config_dir)
            self._migrate_legacy_dir("logs", self.logs_dir)
            self._migrate_legacy_dir("server_files", self.sandboxes_dir)

        # 2. Ensure directories exist
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            self.sandboxes_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            import logging

            logging.error("Failed to initialize runtime directories: %s", exc)
            raise RuntimeError(f"Could not initialize runtime: {exc}") from exc

    def _migrate_legacy_dir(self, legacy_name: str, new_target: Path):
        """
        Moves a legacy directory from the project root into the OS-compliant path.

        Args:
            legacy_name: The name of the old folder (e.g., 'logs').
            new_target: The resolved absolute Path to the new location.

        Returns:
            None.

        Side Effects:
            Mutates the filesystem by recursively copying directories.
            Renames the legacy directory to append a `.migrated` extension.

        Failure Behavior:
            Catches `OSError` and writes a warning to `sys.stderr` rather than
            crashing the application boot sequence.
        """
        legacy_path = self.project_root / legacy_name
        migrated_marker = self.project_root / f"{legacy_name}.migrated"

        if legacy_path.exists() and legacy_path.is_dir() and not migrated_marker.exists():
            try:
                # We use copytree and then rename the old folder to preserve
                # existing setups safely in case of partial failure.
                if not new_target.exists():
                    shutil.copytree(legacy_path, new_target)
                legacy_path.rename(migrated_marker)
            except OSError as exc:
                logger.warning("Failed to migrate legacy %s: %s", legacy_name, exc)
