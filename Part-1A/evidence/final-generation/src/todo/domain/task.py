"""Task entity and enumerations."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import IntEnum, StrEnum
from typing import Any

__all__ = ["Priority", "Status", "Task", "format_utc"]


class Status(StrEnum):
    """Lifecycle state of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Priority(IntEnum):
    """Task priority. The integer value is the sort rank."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @property
    def label(self) -> str:
        """Lowercase name used in input and output."""
        return self.name.lower()


def format_utc(moment: datetime) -> str:
    """Format an aware datetime as UTC ISO-8601 with a trailing Z."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True, slots=True)
class Task:
    """An immutable task."""

    id: int
    title: str
    description: str
    status: Status
    priority: Priority
    tags: tuple[str, ...]
    due_date: date | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-ready representation (without computed fields)."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.label,
            "tags": list(self.tags),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": format_utc(self.created_at),
            "updated_at": format_utc(self.updated_at),
            "completed_at": format_utc(self.completed_at) if self.completed_at else None,
        }
