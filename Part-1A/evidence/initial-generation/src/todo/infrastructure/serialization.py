"""The only module that knows the on-disk JSON shape."""

from datetime import UTC, datetime
from typing import Any

from todo.domain.errors import StorageError, StorageFormatError, ValidationError
from todo.domain.rules import normalize_tags, normalize_title, parse_due_date, parse_priority
from todo.domain.task import Status, Task
from todo.repositories.base import Store

__all__ = ["SUPPORTED_VERSION", "from_dict", "to_dict"]

SUPPORTED_VERSION = 1


def to_dict(store: Store) -> dict[str, Any]:
    """Serialise a store to a JSON-ready dict."""
    return {
        "version": SUPPORTED_VERSION,
        "next_id": store.next_id,
        "tasks": [task.as_dict() for task in store.tasks],
    }


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise StorageFormatError("invalid datetime in data file")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(UTC)
    except ValueError as exc:
        raise StorageFormatError("invalid datetime in data file") from exc


def _task_from_dict(raw: object) -> Task:
    if not isinstance(raw, dict):
        raise StorageFormatError("task entry must be an object")
    try:
        task_id = raw["id"]
        if not isinstance(task_id, int) or isinstance(task_id, bool) or task_id < 1:
            raise StorageFormatError("invalid task id in data file")
        completed = raw["completed_at"]
        return Task(
            id=task_id,
            title=normalize_title(raw["title"]),
            description=str(raw["description"]),
            status=Status(raw["status"]),
            priority=parse_priority(raw["priority"]),
            tags=normalize_tags(raw["tags"]),
            due_date=parse_due_date(raw["due_date"]),
            created_at=_parse_datetime(raw["created_at"]),
            updated_at=_parse_datetime(raw["updated_at"]),
            completed_at=None if completed is None else _parse_datetime(completed),
        )
    except (KeyError, ValueError, TypeError, ValidationError) as exc:
        raise StorageFormatError("task entry is malformed") from exc


def from_dict(document: object) -> Store:
    """Parse and strictly validate a stored document."""
    if not isinstance(document, dict):
        raise StorageFormatError("data file root must be an object")
    version = document.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise StorageFormatError("data file has no valid version")
    if version > SUPPORTED_VERSION:
        raise StorageError(f"data file version {version} is newer than supported")
    if version < 1:
        raise StorageFormatError("data file version is invalid")
    raw_tasks = document.get("tasks")
    next_id = document.get("next_id")
    if not isinstance(raw_tasks, list) or not isinstance(next_id, int):
        raise StorageFormatError("data file is missing 'tasks' or 'next_id'")
    tasks = tuple(_task_from_dict(item) for item in raw_tasks)
    ids = [task.id for task in tasks]
    if len(set(ids)) != len(ids) or (ids and next_id <= max(ids)):
        raise StorageFormatError("task ids are inconsistent")
    return Store(next_id=max(next_id, 1), tasks=tasks)
