from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

import pytest

from todo.domain.errors import InvalidTransitionError, ValidationError
from todo.domain.rules import apply_update, is_overdue, transition
from todo.domain.task import Priority, Status, Task

LATER = datetime(2026, 11, 13, 9, 0, 0, tzinfo=UTC)
TODAY = date(2026, 11, 12)

ALLOWED = {
    (Status.PENDING, Status.IN_PROGRESS),
    (Status.PENDING, Status.COMPLETED),
    (Status.IN_PROGRESS, Status.PENDING),
    (Status.IN_PROGRESS, Status.COMPLETED),
    (Status.COMPLETED, Status.PENDING),
}
ALL_PAIRS = [(a, b) for a in Status for b in Status]


@pytest.mark.parametrize(("source", "target"), ALL_PAIRS)
def test_ac_6_1_and_6_2_full_transition_matrix(
    make_task: Callable[..., Task], source: Status, target: Status
) -> None:
    task = make_task(status=source)
    if (source, target) in ALLOWED:
        result = transition(task, target, LATER)
        assert result.status is target
        assert result.updated_at == LATER
    else:
        with pytest.raises(InvalidTransitionError):
            transition(task, target, LATER)


def test_ac_6_3_completing_sets_completed_at(make_task: Callable[..., Task]) -> None:
    assert transition(make_task(), "completed", LATER).completed_at == LATER


def test_ac_6_4_reopening_clears_completed_at(make_task: Callable[..., Task]) -> None:
    done = transition(make_task(), Status.COMPLETED, LATER)
    assert transition(done, Status.PENDING, LATER).completed_at is None


def test_ac_6_5_unknown_status_is_validation_not_transition_error(
    make_task: Callable[..., Task],
) -> None:
    with pytest.raises(ValidationError):
        transition(make_task(), "archived", LATER)


def test_failed_transition_leaves_task_unchanged(make_task: Callable[..., Task]) -> None:
    task = make_task(status=Status.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        transition(task, Status.IN_PROGRESS, LATER)
    assert task.status is Status.COMPLETED


@pytest.mark.parametrize(
    ("due", "status", "expected"),
    [
        (date(2026, 11, 11), Status.PENDING, True),
        (date(2026, 11, 11), Status.IN_PROGRESS, True),
        (date(2026, 11, 12), Status.PENDING, False),
        (date(2026, 11, 13), Status.PENDING, False),
        (date(2026, 11, 11), Status.COMPLETED, False),
        (None, Status.PENDING, False),
    ],
)
def test_ac_5_8_overdue_rules(
    make_task: Callable[..., Task], due: date | None, status: Status, expected: bool
) -> None:
    assert is_overdue(make_task(status=status, due=due), TODAY) is expected


def test_ac_3_1_partial_update_changes_only_given_fields(make_task: Callable[..., Task]) -> None:
    task = make_task(tags=("a",), due=date(2026, 12, 1))
    result = apply_update(task, LATER, {"priority": "high"})
    assert result.priority is Priority.HIGH
    assert (result.title, result.tags, result.due_date) == (task.title, task.tags, task.due_date)
    assert result.updated_at == LATER
    assert result.created_at == task.created_at


def test_ac_3_2_tags_replaced_and_cleared(make_task: Callable[..., Task]) -> None:
    task = make_task(tags=("a", "b"))
    assert apply_update(task, LATER, {"tags": ["c"]}).tags == ("c",)
    assert apply_update(task, LATER, {"tags": []}).tags == ()


def test_ac_3_3_due_date_can_be_cleared(make_task: Callable[..., Task]) -> None:
    task = make_task(due=date(2026, 12, 1))
    assert apply_update(task, LATER, {"due_date": None}).due_date is None


def test_ac_3_4_invalid_update_leaves_original_unchanged(make_task: Callable[..., Task]) -> None:
    task = make_task()
    with pytest.raises(ValidationError):
        apply_update(task, LATER, {"title": "  "})
    assert task.title == "task"
    assert task.updated_at != LATER


def test_ac_3_5_empty_update_rejected(make_task: Callable[..., Task]) -> None:
    with pytest.raises(ValidationError):
        apply_update(make_task(), LATER, {})


@pytest.mark.parametrize("field", ["status", "id", "created_at"])
def test_ac_3_7_immutable_fields_rejected(make_task: Callable[..., Task], field: str) -> None:
    with pytest.raises(ValidationError):
        apply_update(make_task(), LATER, {field: "x"})


def test_updated_at_moves_forward_by_clock(make_task: Callable[..., Task]) -> None:
    task = make_task()
    assert (
        apply_update(task, task.created_at + timedelta(hours=1), {"title": "n"}).updated_at
        > task.updated_at
    )
