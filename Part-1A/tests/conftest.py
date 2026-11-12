from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from todo.domain.task import Priority, Status, Task
from todo.repositories.base import Store
from todo.services.task_service import TaskService


class FakeClock:
    """Settable clock for deterministic tests."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now += timedelta(**kwargs)


class InMemoryTaskRepository:
    """Repository fake that counts saves."""

    def __init__(self) -> None:
        self.store = Store(next_id=1, tasks=())
        self.save_count = 0

    def load_all(self) -> Store:
        return self.store

    def save_all(self, store: Store) -> None:
        self.store = store
        self.save_count += 1


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 11, 12, 9, 0, 0, tzinfo=UTC))


@pytest.fixture
def repository() -> InMemoryTaskRepository:
    return InMemoryTaskRepository()


@pytest.fixture
def service(repository: InMemoryTaskRepository, clock: FakeClock) -> TaskService:
    return TaskService(repository, clock)


@pytest.fixture
def make_task(clock: FakeClock) -> Callable[..., Task]:
    def _make(
        id: int = 1,
        title: str = "task",
        status: Status = Status.PENDING,
        priority: Priority = Priority.MEDIUM,
        tags: tuple[str, ...] = (),
        due: date | None = None,
        created: datetime | None = None,
    ) -> Task:
        moment = created or clock.now()
        return Task(id, title, "", status, priority, tags, due, moment, moment, None)

    return _make


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    return tmp_path / "data" / "todo_data.json"
