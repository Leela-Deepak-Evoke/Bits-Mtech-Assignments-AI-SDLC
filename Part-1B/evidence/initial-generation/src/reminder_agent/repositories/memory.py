"""Reminder stores behind one small interface (FR-7): in-memory, and atomic JSON file."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from reminder_agent.errors import StorageError
from reminder_agent.models import Reminder


class MemoryStore:
    """In-memory store. ``commit`` is all-or-nothing and the only mutation entry point."""

    def __init__(self, reminders: list[Reminder] | None = None) -> None:
        self._items: dict[str, Reminder] = {r.id: r for r in reminders or []}
        self._ever_used: set[str] = set(self._items)

    def get(self, reminder_id: str) -> Reminder | None:
        return self._items.get(reminder_id)

    def list(self) -> list[Reminder]:
        return sorted(self._items.values(), key=lambda r: r.id)

    def snapshot(self) -> list[dict[str, object]]:
        """Deterministic JSON-able view used for byte-identical comparisons (INV-7/8)."""
        return [r.to_dict() for r in self.list()]

    def commit(self, add: Reminder | None = None, update: Reminder | None = None) -> None:
        staged = dict(self._items)
        if add is not None:
            if add.id in self._ever_used:
                raise StorageError("id reuse")
            staged[add.id] = add
        if update is not None:
            if update.id not in staged:
                raise StorageError("unknown reminder")
            staged[update.id] = update
        self._persist(staged)
        self._items = staged
        self._ever_used.update(staged)

    def _persist(self, items: dict[str, Reminder]) -> None:  # noqa: B027 - intentional hook
        """Hook for durable subclasses; the in-memory store has nothing to do."""


class JsonFileStore(MemoryStore):
    """JSON file store: temp file in the same directory then ``os.replace`` (atomic, AC-7.2)."""

    def __init__(self, path: Path) -> None:
        self._path = path
        loaded: list[Reminder] = []
        if path.exists():
            try:
                loaded = [Reminder.from_dict(d) for d in json.loads(path.read_text(encoding="utf-8"))["reminders"]]
            except (OSError, ValueError, KeyError) as exc:
                raise StorageError("unreadable store file") from exc
        super().__init__(loaded)

    def _persist(self, items: dict[str, Reminder]) -> None:
        payload = {"version": 1, "reminders": [r.to_dict() for r in sorted(items.values(), key=lambda r: r.id)]}
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False)
                os.replace(tmp, self._path)
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise StorageError("write failed") from exc
