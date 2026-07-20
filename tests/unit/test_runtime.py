"""
Module: test_runtime.py
───────────────────────
Purpose: Validates OS path resolution and portable mode toggles.

Architectural Role:
Unit testing for the `RuntimeEnvironment` component. Ensures that configuration 
and log data lands in the correct XDG/APPDATA/Library locations on different OSs.

Responsibilities:
- Verify portable mode redirects all writes to the local binary folder.
- Verify OS-specific data directories are resolved correctly.
- Verify migration logic safely moves legacy data without deleting it.

Expected Collaborators:
- `pytest` (test runner).
- `src.core.runtime.RuntimeEnvironment` (the subject under test).
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

from src.core.runtime import RuntimeEnvironment


def test_portable_mode(tmp_path):
    """
    Validates that portable mode encapsulates all data paths.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Side Effects:
        Touches a `.portable` file in the temporary directory.

    Failure Behavior:
        Fails if data paths leak out to the host OS.
    """
    # Create the .portable marker
    (tmp_path / ".portable").touch()
    
    runtime = RuntimeEnvironment(tmp_path)
    assert runtime.is_portable is True
    assert runtime.data_dir == tmp_path / "runtime"
    assert runtime.config_dir == tmp_path / "runtime" / "config"
    assert runtime.logs_dir == tmp_path / "runtime" / "logs"
    assert runtime.sandboxes_dir == tmp_path / "runtime" / "server_files"


def test_windows_path_resolution(tmp_path):
    """
    Validates Windows-specific data path resolution.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Side Effects:
        Mocks `sys.platform` and `os.environ`.

    Failure Behavior:
        Fails if it does not use `APPDATA`.
    """
    with patch("sys.platform", "win32"), patch.dict(os.environ, {"APPDATA": str(tmp_path / "AppData")}):
        runtime = RuntimeEnvironment(tmp_path)
        assert runtime.is_portable is False
        assert runtime.data_dir == tmp_path / "AppData" / "CS4S"


def test_macos_path_resolution(tmp_path):
    """
    Validates macOS-specific data path resolution.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Side Effects:
        Mocks `sys.platform`.

    Failure Behavior:
        Fails if it does not use `~/Library/Application Support`.
    """
    with patch("sys.platform", "darwin"):
        runtime = RuntimeEnvironment(tmp_path)
        assert runtime.is_portable is False
        assert runtime.data_dir == Path.home() / "Library" / "Application Support" / "CS4S"


def test_linux_path_resolution(tmp_path):
    """
    Validates Linux-specific data path resolution.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Side Effects:
        Mocks `sys.platform` and `os.environ`.

    Failure Behavior:
        Fails if it does not use `XDG_DATA_HOME`.
    """
    with patch("sys.platform", "linux"), patch.dict(os.environ, {"XDG_DATA_HOME": str(tmp_path / "xdg")}):
        runtime = RuntimeEnvironment(tmp_path)
        assert runtime.is_portable is False
        assert runtime.data_dir == tmp_path / "xdg" / "CS4S"


def test_bootstrap_migration(tmp_path):
    """
    Validates the legacy data migration sequence.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.

    Side Effects:
        Creates and renames directories on the temporary disk.

    Failure Behavior:
        Fails if the original folder is permanently deleted instead of renamed.
    """
    # Create legacy data
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.json").touch()
    
    # We will simulate Windows migration
    with patch("sys.platform", "win32"), patch.dict(os.environ, {"APPDATA": str(tmp_path / "AppData")}):
        runtime = RuntimeEnvironment(tmp_path)
        runtime.bootstrap()
        
        # New directory should be created
        assert (tmp_path / "AppData" / "CS4S" / "config").exists()
        assert (tmp_path / "AppData" / "CS4S" / "config" / "settings.json").exists()
        
        # Legacy directory should be renamed
        assert not (tmp_path / "config").exists()
        assert (tmp_path / "config.migrated").exists()
