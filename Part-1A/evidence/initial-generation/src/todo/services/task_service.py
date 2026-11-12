"""Use-cases shared by the CLI and the API."""

import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from todo.domain import rules
from todo.domain.errors import TaskNotFoundError
from todo.domain.query import filter_tasks, sort_tasks
from todo.domain.smart.next_task import select_next
from todo.domain.task import Task
from todo.repositories.base import Store, TaskRepository
from todo.services.ports import Clock

__all__ = ["TaskService", "TaskView"]


@dataclass(frozen=True, slots=True)
class TaskView:
    """A task plus computed fields, as returned to interfaces."""

    task: Task
    overdue: bool

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-ready representation including ``overdue``."""
        return {**self.task.as_dict(), "overdue": self.overdue}


class TaskService:
    """Orchestrates load -> pure domain rule -> save."""

    def __init__(self, repository: TaskRepository, clock: Clock) -> None:
        """Create a service over a repository and a clock."""
        self._repository = repository
        self._clock = clock
        self._lock = threading.RLock()

    def _view(self, task: Task) -> TaskView:
        return TaskView(task, rules.is_overdue(task, self._clock.now().date()))

    @staticmethod
    def _find(store: Store, task_id: int) -> Task:
        for task in store.tasks:
            if task.id == task_id:
                return task
        raise TaskNotFoundError(f"task {task_id} not found")

    def add_task(self, data: Mapping[str, object]) -> TaskView:
        """Create a task."""
        with self._lock:
            store = self._repository.load_all()
            task = rules.build_task(store.next_id, self._clock.now(), data)
            self._repository.save_all(Store(store.next_id + 1, (*store.tasks, task)))
            return self._view(task)

    def get_task(self, task_id: int) -> TaskView:
        """Return one task."""
        with self._lock:
            return self._view(self._find(self._repository.load_all(), task_id))

    def list_tasks(  # noqa: PLR0913
        self,
        *,
        status: object = None,
        priority: object = None,
        tags: Sequence[str] = (),
        match: str = "all",
        overdue: bool | None = None,
        sort: str = "priority",
        order: str | None = None,
    ) -> list[TaskView]:
        """Filter, then sort, the stored tasks."""
        with self._lock:
            store = self._repository.load_all()
        today = self._clock.now().date()
        filtered = filter_tasks(
            store.tasks,
            today=today,
            status=status,
            priority=priority,
            tags=tags,
            match=match,
            overdue=overdue,
        )
        return [self._view(task) for task in sort_tasks(filtered, key=sort, order=order)]

    def update_task(self, task_id: int, changes: Mapping[str, object]) -> TaskView:
        """Apply a partial update."""
        with self._lock:
            store = self._repository.load_all()
            current = self._find(store, task_id)
            updated = rules.apply_update(current, self._clock.now(), changes)
            self._replace(store, updated)
            return self._view(updated)

    def delete_task(self, task_id: int) -> None:
        """Delete a task; its id is never reused."""
        with self._lock:
            store = self._repository.load_all()
            self._find(store, task_id)
            remaining = tuple(task for task in store.tasks if task.id != task_id)
            self._repository.save_all(replace(store, tasks=remaining))

    def change_status(self, task_id: int, new_status: object) -> TaskView:
        """Transition a task to a new status."""
        with self._lock:
            store = self._repository.load_all()
            current = self._find(store, task_id)
            updated = rules.transition(current, new_status, self._clock.now())
            self._replace(store, updated)
            return self._view(updated)

    def next_task(self) -> TaskView | None:
        """Return the most actionable task, if any."""
        with self._lock:
            store = self._repository.load_all()
        chosen = select_next(store.tasks, self._clock.now().date())
        return self._view(chosen) if chosen else None

    def _replace(self, store: Store, updated: Task) -> None:
        tasks = tuple(updated if task.id == updated.id else task for task in store.tasks)
        self._repository.save_all(replace(store, tasks=tasks))
