"""Pure filtering and sorting of tasks."""

from collections.abc import Callable, Iterable, Sequence
from datetime import date

from todo.domain.errors import ValidationError
from todo.domain.rules import is_overdue, parse_priority, parse_status
from todo.domain.task import Task

__all__ = ["MATCH_MODES", "SORT_KEYS", "filter_tasks", "sort_tasks"]

MATCH_MODES = ("all", "any")
SORT_KEYS = ("priority", "due_date", "created_at", "id")
SORT_ORDERS = ("asc", "desc")

_SORT_FUNCTIONS: dict[str, Callable[[Task], object]] = {
    "priority": lambda task: task.priority.value,
    "created_at": lambda task: task.created_at,
    "id": lambda task: task.id,
}


def filter_tasks(  # noqa: PLR0913
    tasks: Iterable[Task],
    *,
    today: date,
    status: object = None,
    priority: object = None,
    tags: Sequence[str] = (),
    match: str = "all",
    overdue: bool | None = None,
) -> list[Task]:
    """Return tasks satisfying every given filter (logical AND)."""
    if match not in MATCH_MODES:
        raise ValidationError("match must be one of: all, any")
    wanted_status = parse_status(status) if status is not None else None
    wanted_priority = parse_priority(priority) if priority is not None else None
    wanted_tags = tuple(dict.fromkeys(tag.strip().lower() for tag in tags))
    combine = all if match == "all" else any

    def keep(task: Task) -> bool:
        if wanted_status is not None and task.status is not wanted_status:
            return False
        if wanted_priority is not None and task.priority is not wanted_priority:
            return False
        if wanted_tags and not combine(tag in task.tags for tag in wanted_tags):
            return False
        return overdue is None or is_overdue(task, today) is overdue

    return [task for task in tasks if keep(task)]


def sort_tasks(
    tasks: Iterable[Task], *, key: str = "priority", order: str | None = None
) -> list[Task]:
    """Sort tasks by ``key``; ties are always broken by ascending id.

    Priority defaults to descending order, every other key to ascending.
    Tasks without a due date are placed last in both directions.
    """
    if key not in SORT_KEYS:
        raise ValidationError(f"sort must be one of: {', '.join(SORT_KEYS)}")
    if order is not None and order not in SORT_ORDERS:
        raise ValidationError("order must be one of: asc, desc")
    reverse = (order == "desc") if order is not None else key == "priority"
    by_id = sorted(tasks, key=lambda task: task.id)
    if key == "due_date":
        dated = [task for task in by_id if task.due_date is not None]
        undated = [task for task in by_id if task.due_date is None]
        dated.sort(key=lambda task: task.due_date or date.max, reverse=reverse)
        return dated + undated
    return sorted(by_id, key=_SORT_FUNCTIONS[key], reverse=reverse)  # type: ignore[arg-type]
