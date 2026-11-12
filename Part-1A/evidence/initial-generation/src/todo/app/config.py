"""Environment-driven settings."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

__all__ = ["Settings"]

DEFAULT_DATA_FILE = "todo_data.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration."""

    data_file: Path = Path(DEFAULT_DATA_FILE)
    api_key: str | None = None
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        """Build settings from ``TODO_*`` environment variables."""
        source = os.environ if env is None else env
        return cls(
            data_file=Path(source.get("TODO_DATA_FILE") or DEFAULT_DATA_FILE),
            api_key=source.get("TODO_API_KEY") or None,
            host=source.get("TODO_HOST") or DEFAULT_HOST,
            port=int(source.get("TODO_PORT") or DEFAULT_PORT),
        )
