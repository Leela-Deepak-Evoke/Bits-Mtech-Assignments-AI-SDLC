"""JSON-file implementation of the task repository."""

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from todo.domain.errors import StorageError, StorageFormatError
from todo.infrastructure import serialization
from todo.infrastructure.file_io import atomic_write_text, read_bytes_if_exists
from todo.repositories.base import Store

__all__ = ["JsonFileTaskRepository"]

_LOGGER = logging.getLogger(__name__)


class JsonFileTaskRepository:
    """Stores all tasks in a single JSON file."""

    def __init__(self, path: Path, on_warning: Callable[[str], None] | None = None) -> None:
        """Bind to ``path``; ``on_warning`` receives recovery notices."""
        self._path = path
        self._on_warning = on_warning or _LOGGER.warning

    def load_all(self) -> Store:
        """Load the store, quarantining a corrupt file instead of failing."""
        raw = read_bytes_if_exists(self._path)
        if raw is None:
            return Store(next_id=1, tasks=())
        try:
            return serialization.from_dict(json.loads(raw.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError, StorageFormatError):
            self._quarantine()
            return Store(next_id=1, tasks=())

    def save_all(self, store: Store) -> None:
        """Atomically persist the store."""
        text = json.dumps(serialization.to_dict(store), indent=2, ensure_ascii=False) + "\n"
        atomic_write_text(self._path, text)

    def _quarantine(self) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        target = self._path.with_name(f"{self._path.name}.corrupt-{stamp}")
        counter = 1
        while target.exists():
            target = self._path.with_name(f"{self._path.name}.corrupt-{stamp}-{counter}")
            counter += 1
        try:
            self._path.replace(target)
        except OSError as exc:
            raise StorageError("cannot quarantine corrupt data file") from exc
        self._on_warning(f"data file was corrupt; moved to {target.name} and started empty")
