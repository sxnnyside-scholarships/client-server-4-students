"""
Module: config.py
─────────────────
Purpose: Handles loading and saving application settings from a JSON file.

Architectural Role:
Provides a centralized, single-source-of-truth for all runtime preferences
(locale, theme, server ports) across both the Client and Server applications.

Responsibilities:
- Abstract file I/O for JSON configuration.
- Provide sensible defaults for first-time users.
- Support deep dictionary traversal for nested configuration keys.

Expected Collaborators:
- `src.ui.launcher`, `src.ui.client_window`, `src.ui.server_window`
- `src.core.runtime` (to determine where the config file is stored)
"""

import json
from pathlib import Path


class ConfigManager:
    """
    Manages application configuration stored in a JSON file.

    Why it exists:
    Provides a persistent storage mechanism for application settings, ensuring
    user preferences survive across application reboots.

    Responsibilities:
    - Serializing and deserializing JSON.
    - Merging default settings if the configuration file is missing or corrupted.

    Non-Responsibilities (Anti-Goals):
    - It does NOT determine where the file is stored on disk (delegated to `RuntimeEnvironment`).
    - It does NOT apply the settings (e.g., changing the UI theme). It merely stores the values.
    """

    # Sensible defaults for first-time users
    DEFAULTS = {
        "locale": "en",
        "theme": "mint_light",
        "server": {
            "host": "0.0.0.0",
            "port": 2121,
            "max_connections": 5,
            "enable_tls": False,
            "cert_file": "cert.pem",
            "key_file": "key.pem",
        },
        "client": {
            "default_host": "localhost",
            "default_port": 2121,
            "enable_tls": False,
        },
    }

    def __init__(self, config_path: str | Path):
        self.path = Path(config_path)
        self.data: dict = {}
        self._load()

    # ── persistence ───────────────────────────────────────────

    def _load(self):
        """Load settings from file, or create defaults if the file is
        missing or corrupted."""
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    self.data = json.load(fh)
                return
            except (json.JSONDecodeError, IOError):
                pass  # fall through to defaults
        self.data = json.loads(json.dumps(self.DEFAULTS))  # deep copy
        self._save()

    def _save(self):
        """Write current settings to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=4, ensure_ascii=False)

    # ── public API ────────────────────────────────────────────

    def get(self, key: str, default=None):
        """
        Retrieves a top-level setting value.

        Args:
            key: The string identifier of the setting.
            default: The fallback value if the key does not exist.

        Returns:
            The value associated with the key, or the default value.

        Side Effects:
            None. Reads from in-memory dictionary.

        Failure Behavior:
            Returns the `default` parameter if the key is missing.
        """
        return self.data.get(key, default)

    def set(self, key: str, value):
        """
        Sets a top-level setting and persists it to disk.

        Args:
            key: The string identifier of the setting.
            value: The data to store (must be JSON serializable).

        Returns:
            None.

        Side Effects:
            Mutates the in-memory dictionary.
            Writes the entire JSON configuration to the host filesystem.

        Failure Behavior:
            Raises `TypeError` if the value is not JSON serializable.
            Raises `IOError` if the disk is un-writable.
        """
        self.data[key] = value
        self._save()

    def get_nested(self, *keys, default=None):
        """
        Retrieves a deeply nested setting value safely.

        Args:
            *keys: An ordered sequence of string keys representing the nested path.
            default: The fallback value if any part of the path does not exist.

        Returns:
            The deeply nested value, or the default value.

        Side Effects:
            None. Reads from in-memory dictionary.

        Failure Behavior:
            Returns `default` if the key path is broken or traverses a non-dictionary node.
        """
        current = self.data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            else:
                return default
        return current

    def set_nested(self, *keys_and_value):
        """
        Sets a deeply nested setting and persists it to disk.

        Args:
            *keys_and_value: An ordered sequence of string keys, where the final
                             argument is the value to store.

        Returns:
            None.

        Side Effects:
            Mutates the in-memory dictionary (creating intermediate dictionaries if needed).
            Writes the entire JSON configuration to the host filesystem.

        Failure Behavior:
            Overwrites intermediate non-dictionary nodes destructively if encountered.
            Raises `TypeError` if the value is not JSON serializable.
            Raises `IOError` if the disk is un-writable.
        """
        *keys, value = keys_and_value
        current = self.data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self._save()
