"""Human-readable and JSON output formatting."""

import json
from typing import Any

from todo.services.task_service import TaskView

__all__ = ["task_detail", "task_line", "to_json"]


def to_json(payload: Any) -> str:  # noqa: ANN401
    """Pretty JSON that preserves Unicode."""
    return json.dumps(payload, indent=2, ensure_ascii=False)


def task_line(view: TaskView) -> str:
    """One-line summary of a task."""
    task = view.task
    parts = [
        f"{task.id:>4}",
        f"[{task.status.value}]",
        f"{task.priority.label:<6}",
        task.title,
    ]
    if task.tags:
        parts.append(" ".join(f"#{tag}" for tag in task.tags))
    if task.due_date:
        parts.append(f"due:{task.due_date.isoformat()}")
    if view.overdue:
        parts.append("OVERDUE")
    return "  ".join(parts)


def task_detail(view: TaskView) -> str:
    """Multi-line detail of a task."""
    data = view.as_dict()
    lines = [f"{key:<12}{value}" for key, value in data.items()]
    return "\n".join(lines)
