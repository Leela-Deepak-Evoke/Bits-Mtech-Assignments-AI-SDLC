"""Repository interface: the whole task store is loaded and saved as one unit."""

from dataclasses import dataclass
from typing import Protocol

from todo.domain.task import Task

__all__ = ["Store", "TaskRepository"]


@dataclass(frozen=True, slots=True)
class Store:
    """Complete persisted state."""

    next_id: int
    tasks: tuple[Task, ...]


class TaskRepository(Protocol):
    """Loads and atomically saves the task store."""

    def load_all(self) -> Store:
        """Return the stored state (an empty store when nothing exists)."""
        ...

    def save_all(self, store: Store) -> None:
        """Persist ``store`` atomically."""
        ...
