"""Composition root: the only place concrete adapters are wired together."""

from collections.abc import Callable

from todo.app.config import Settings
from todo.infrastructure.clock import SystemClock
from todo.infrastructure.json_repository import JsonFileTaskRepository
from todo.services.ports import Clock
from todo.services.task_service import TaskService

__all__ = ["build_service"]


def build_service(
    settings: Settings,
    clock: Clock | None = None,
    on_warning: Callable[[str], None] | None = None,
) -> TaskService:
    """Create a TaskService backed by the JSON file named in ``settings``."""
    repository = JsonFileTaskRepository(settings.data_file, on_warning)
    return TaskService(repository, clock or SystemClock())
