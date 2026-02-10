"""
Configuration Manager
─────────────────────
Handles loading and saving application settings from a JSON file.
Settings include locale, theme, server port, and other preferences.
The file is human-readable and easy to edit by hand.
"""

import json
from pathlib import Path


class ConfigManager:
    """Manages application configuration stored in a JSON file."""

    # Sensible defaults for first-time users
    DEFAULTS = {
        "locale": "en",
        "theme": "mint_light",
        "server": {
            "host": "0.0.0.0",
            "port": 2121,
            "max_connections": 5,
        },
        "client": {
            "default_host": "localhost",
            "default_port": 2121,
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
        """Get a top-level setting value."""
        return self.data.get(key, default)

    def set(self, key: str, value):
        """Set a top-level setting and persist to disk."""
        self.data[key] = value
        self._save()

    def get_nested(self, *keys, default=None):
        """Get a nested setting value.

        Example::

            config.get_nested("server", "port", default=2121)
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
        """Set a nested setting.  The **last** positional argument is
        the value; everything before it is the key path.

        Example::

            config.set_nested("server", "port", 3000)
        """
        *keys, value = keys_and_value
        current = self.data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self._save()
