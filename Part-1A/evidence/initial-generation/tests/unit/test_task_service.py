import pytest

from conftest import FakeClock, InMemoryTaskRepository
from todo.domain.errors import (
    InvalidTransitionError,
    TaskNotFoundError,
    ValidationError,
)
from todo.services.task_service import TaskService


def test_ac_1_1_and_1_9_add_assigns_incrementing_ids(service: TaskService) -> None:
    first = service.add_task({"title": "a"})
    second = service.add_task({"title": "b"})
    assert (first.task.id, second.task.id) == (1, 2)
    assert first.task.status.value == "pending"


def test_ac_1_2_invalid_add_stores_nothing(
    service: TaskService, repository: InMemoryTaskRepository
) -> None:
    with pytest.raises(ValidationError):
        service.add_task({"title": " "})
    assert repository.save_count == 0
    assert service.list_tasks() == []


def test_ac_2_1_get_includes_computed_overdue(service: TaskService) -> None:
    service.add_task({"title": "late", "due_date": "2026-11-01"})
    assert service.get_task(1).overdue is True
    assert service.get_task(1).as_dict()["overdue"] is True


def test_ac_2_2_get_unknown_id_not_found(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.get_task(99)


def test_ac_2_3_list_on_empty_store(service: TaskService) -> None:
    assert service.list_tasks() == []


def test_ac_3_1_update_bumps_updated_at(service: TaskService, clock: FakeClock) -> None:
    service.add_task({"title": "a"})
    clock.advance(hours=1)
    view = service.update_task(1, {"priority": "high"})
    assert view.task.updated_at > view.task.created_at


def test_ac_3_4_failed_update_does_not_save(
    service: TaskService, repository: InMemoryTaskRepository
) -> None:
    service.add_task({"title": "a"})
    saves = repository.save_count
    with pytest.raises(ValidationError):
        service.update_task(1, {"title": ""})
    assert repository.save_count == saves
    assert service.get_task(1).task.title == "a"


def test_ac_3_6_update_unknown_id(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.update_task(5, {"title": "x"})


def test_ac_4_1_and_4_2_delete(service: TaskService) -> None:
    service.add_task({"title": "a"})
    service.delete_task(1)
    with pytest.raises(TaskNotFoundError):
        service.get_task(1)
    with pytest.raises(TaskNotFoundError):
        service.delete_task(1)


def test_ac_4_3_ids_are_never_reused(service: TaskService) -> None:
    for title in "abc":
        service.add_task({"title": title})
    service.delete_task(3)
    assert service.add_task({"title": "d"}).task.id == 4


def test_ac_6_status_changes_persist_and_invalid_ones_do_not_save(
    service: TaskService, repository: InMemoryTaskRepository
) -> None:
    service.add_task({"title": "a"})
    assert service.change_status(1, "in_progress").task.status.value == "in_progress"
    saves = repository.save_count
    with pytest.raises(InvalidTransitionError):
        service.change_status(1, "in_progress")
    assert repository.save_count == saves


def test_ac_6_6_status_change_unknown_id(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.change_status(1, "completed")


def test_list_filters_then_sorts(service: TaskService) -> None:
    service.add_task({"title": "low", "priority": "low", "tags": ["x"]})
    service.add_task({"title": "high", "priority": "high", "tags": ["x"]})
    service.add_task({"title": "other", "priority": "high"})
    titles = [view.task.title for view in service.list_tasks(tags=["x"])]
    assert titles == ["high", "low"]


def test_ac_8_3_next_task_none_when_empty(service: TaskService) -> None:
    assert service.next_task() is None


def test_next_task_returns_view(service: TaskService) -> None:
    service.add_task({"title": "a"})
    view = service.next_task()
    assert view is not None
    assert view.task.title == "a"
