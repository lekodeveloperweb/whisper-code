from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_CONFIG: dict[str, str | int | bool | None] = {
    "api_url": "http://localhost:8080",
    "model_name": "whisper-large-v3",
    "model_quality": "accurate",
    "hotkey": "Cmd+Ctrl+T",
    "auto_insert": True,
    "sample_rate": 16000,
    "use_grammar_check": True,
    "grammar_model": "gemma4-e4b-8b",
    "silence_threshold_ms": 800,
    "voice_commands_enabled": True,
}

ENV_MAP: dict[str, tuple[str, type]] = {
    "api_url": ("WHISPER_API_URL", str),
    "model_name": ("WHISPER_MODEL_NAME", str),
    "model_quality": ("WHISPER_MODEL_QUALITY", str),
    "hotkey": ("WHISPER_HOTKEY", str),
    "auto_insert": ("WHISPER_AUTO_INSERT", bool),
    "sample_rate": ("WHISPER_SAMPLE_RATE", int),
    "use_grammar_check": ("WHISPER_GRAMMAR_CHECK", bool),
    "grammar_model": ("WHISPER_GRAMMAR_MODEL", str),
    "silence_threshold_ms": ("WHISPER_SILENCE_THRESHOLD", int),
    "voice_commands_enabled": ("WHISPER_VOICE_COMMANDS", bool),
}


class ConfigManager:
    """Manages Whisper-Code configuration.

    Configuration is loaded from three sources in order of priority:
    1. Default values (lowest priority)
    2. ~/.config/whisper-code/settings.json file
    3. Environment variables (highest priority)

    Env var overrides are defined in ENV_MAP.
    """

    def __init__(self) -> None:
        """Initialize config manager and load configuration."""
        self.config_dir: Path = Path.home() / ".config" / "whisper-code"
        self.config_file: Path = self.config_dir / "settings.json"
        self.config: dict[str, str | int | bool | None] = self.load_config()

    @staticmethod
    def _parse_env_value(value: str, target_type: type) -> str | int | bool:
        """Parse an environment variable string to its target type."""
        if target_type is bool:
            return value.lower() in ("true", "1")
        if target_type is int:
            return int(value)
        return value

    def load_config(self) -> dict[str, str | int | bool | None]:
        """Load configuration from defaults, file, and environment variables.

        Merges DEFAULT_CONFIG with any file overrides, then applies
        environment variable overrides on top.
        """
        config: dict[str, str | int | bool | None] = dict(DEFAULT_CONFIG)
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception:
                pass
        for key, (env_name, target_type) in ENV_MAP.items():
            env_value = os.environ.get(env_name)
            if env_value is not None and env_value != "":
                config[key] = self._parse_env_value(env_value, target_type)
        return config

    def save_config(self, config_updates: dict[str, str | int | bool]) -> None:
        """Persist config updates to the settings JSON file.

        Merges updates into the current config and writes the
        complete config to disk.
        """
        self.config.update(config_updates)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key: str) -> str | int | bool | None:
        """Retrieve a configuration value by key."""
        return self.config.get(key)

    def reload(self) -> dict[str, str | int | bool | None]:
        """Reload configuration from all sources (defaults, file, env vars).

        Returns the merged config dict. Use this to pick up changes
        written by save_config() or environment variable changes.
        """
        self.config = self.load_config()
        return self.config
