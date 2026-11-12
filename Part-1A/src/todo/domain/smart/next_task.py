"""Select the single most actionable task."""

from collections.abc import Iterable
from datetime import date

from todo.domain.rules import is_overdue
from todo.domain.task import Status, Task

__all__ = ["select_next"]


def select_next(tasks: Iterable[Task], today: date) -> Task | None:
    """Pick the next task: overdue, priority, due date, in-progress, then id."""
    candidates = [task for task in tasks if task.status is not Status.COMPLETED]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda task: (
            not is_overdue(task, today),
            -task.priority.value,
            task.due_date or date.max,
            task.status is not Status.IN_PROGRESS,
            task.id,
        ),
    )
