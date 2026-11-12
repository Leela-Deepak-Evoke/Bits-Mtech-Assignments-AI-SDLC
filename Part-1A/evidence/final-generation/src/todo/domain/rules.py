"""Pure business rules: validation, creation, updates, transitions, overdue."""

import re
from collections.abc import Iterable, Mapping
from dataclasses import replace
from datetime import date, datetime

from todo.domain.errors import InvalidTransitionError, ValidationError
from todo.domain.task import Priority, Status, Task

__all__ = [
    "MUTABLE_FIELDS",
    "apply_update",
    "build_task",
    "is_overdue",
    "normalize_description",
    "normalize_tags",
    "normalize_title",
    "parse_due_date",
    "parse_priority",
    "parse_status",
    "transition",
]

TITLE_MAX = 200
DESCRIPTION_MAX = 2000
TAG_MAX_LENGTH = 30
TAG_MAX_COUNT = 10

MUTABLE_FIELDS = frozenset({"title", "description", "priority", "tags", "due_date"})

_TAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.PENDING: frozenset({Status.IN_PROGRESS, Status.COMPLETED}),
    Status.IN_PROGRESS: frozenset({Status.PENDING, Status.COMPLETED}),
    Status.COMPLETED: frozenset({Status.PENDING}),
}


def normalize_title(value: object) -> str:
    """Trim a title and enforce 1..200 characters."""
    if not isinstance(value, str):
        raise ValidationError("title must be a string")
    title = value.strip()
    if not title:
        raise ValidationError("title must not be empty")
    if len(title) > TITLE_MAX:
        raise ValidationError(f"title must be at most {TITLE_MAX} characters")
    return title


def normalize_description(value: object) -> str:
    """Validate a description (0..2000 characters)."""
    if not isinstance(value, str):
        raise ValidationError("description must be a string")
    if len(value) > DESCRIPTION_MAX:
        raise ValidationError(f"description must be at most {DESCRIPTION_MAX} characters")
    return value


def normalize_tags(values: object) -> tuple[str, ...]:
    """Lowercase, validate and de-duplicate tags, preserving first-seen order."""
    if isinstance(values, str) or not isinstance(values, Iterable):
        raise ValidationError("tags must be a list of strings")
    seen: dict[str, None] = {}
    for raw in values:
        if not isinstance(raw, str):
            raise ValidationError("each tag must be a string")
        tag = raw.strip().lower()
        if not tag or len(tag) > TAG_MAX_LENGTH:
            raise ValidationError(f"each tag must be 1..{TAG_MAX_LENGTH} characters")
        if not _TAG_PATTERN.match(tag):
            raise ValidationError(f"invalid tag {tag!r}: use letters, digits, '_' or '-'")
        seen[tag] = None
    if len(seen) > TAG_MAX_COUNT:
        raise ValidationError(f"at most {TAG_MAX_COUNT} tags are allowed")
    return tuple(seen)


def parse_priority(value: object) -> Priority:
    """Convert user input to a Priority."""
    if isinstance(value, Priority):
        return value
    if isinstance(value, str):
        try:
            return Priority[value.strip().upper()]
        except KeyError:
            pass
    raise ValidationError("priority must be one of: low, medium, high")


def parse_status(value: object) -> Status:
    """Convert user input to a Status."""
    if isinstance(value, Status):
        return value
    if isinstance(value, str):
        try:
            return Status(value.strip().lower())
        except ValueError:
            pass
    raise ValidationError("status must be one of: pending, in_progress, completed")


def parse_due_date(value: object) -> date | None:
    """Parse an ISO ``YYYY-MM-DD`` date, or ``None``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        raise ValidationError("due_date must be a date (YYYY-MM-DD)")
    if isinstance(value, date):
        return value
    if isinstance(value, str) and _DATE_PATTERN.match(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValidationError("due_date must be a valid date in YYYY-MM-DD format")


def _reject_unknown(data: Mapping[str, object], action: str) -> None:
    unknown = sorted(set(data) - MUTABLE_FIELDS)
    if unknown:
        raise ValidationError(f"cannot {action} field(s): {', '.join(unknown)}")


def build_task(task_id: int, now: datetime, data: Mapping[str, object]) -> Task:
    """Create a new pending task from user-supplied fields."""
    _reject_unknown(data, "set")
    if "title" not in data:
        raise ValidationError("title is required")
    return Task(
        id=task_id,
        title=normalize_title(data["title"]),
        description=normalize_description(data.get("description", "")),
        status=Status.PENDING,
        priority=parse_priority(data.get("priority", Priority.MEDIUM)),
        tags=normalize_tags(data.get("tags", ())),
        due_date=parse_due_date(data.get("due_date")),
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def apply_update(task: Task, now: datetime, changes: Mapping[str, object]) -> Task:
    """Return a copy of ``task`` with the given changes applied."""
    _reject_unknown(changes, "update")
    if not changes:
        raise ValidationError("no fields to update")
    updated = task
    if "title" in changes:
        updated = replace(updated, title=normalize_title(changes["title"]))
    if "description" in changes:
        updated = replace(updated, description=normalize_description(changes["description"]))
    if "priority" in changes:
        updated = replace(updated, priority=parse_priority(changes["priority"]))
    if "tags" in changes:
        updated = replace(updated, tags=normalize_tags(changes["tags"]))
    if "due_date" in changes:
        updated = replace(updated, due_date=parse_due_date(changes["due_date"]))
    return replace(updated, updated_at=now)


def transition(task: Task, new_status: object, now: datetime) -> Task:
    """Move a task to ``new_status`` if the transition table allows it."""
    target = parse_status(new_status)
    if target not in _TRANSITIONS[task.status]:
        raise InvalidTransitionError(
            f"cannot change status from {task.status.value} to {target.value}"
        )
    completed_at = now if target is Status.COMPLETED else None
    return replace(task, status=target, updated_at=now, completed_at=completed_at)


def is_overdue(task: Task, today: date) -> bool:
    """A task is overdue when it has a past due date and is not completed."""
    return (
        task.due_date is not None and task.due_date < today and task.status is not Status.COMPLETED
    )
