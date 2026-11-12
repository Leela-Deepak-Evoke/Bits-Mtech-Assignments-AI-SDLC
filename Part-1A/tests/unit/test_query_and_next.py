from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

import pytest

from todo.domain.errors import ValidationError
from todo.domain.query import filter_tasks, sort_tasks
from todo.domain.smart.next_task import select_next
from todo.domain.task import Priority, Status, Task

TODAY = date(2026, 11, 12)


def ids(tasks: list[Task]) -> list[int]:
    return [task.id for task in tasks]


@pytest.fixture
def tagged(make_task: Callable[..., Task]) -> list[Task]:
    return [
        make_task(id=1, tags=("work", "urgent")),
        make_task(id=2, tags=("work",)),
        make_task(id=3),
    ]


def test_ac_5_1_single_tag(tagged: list[Task]) -> None:
    assert ids(filter_tasks(tagged, today=TODAY, tags=["work"])) == [1, 2]


def test_ac_5_2_multiple_tags_match_all(tagged: list[Task]) -> None:
    assert ids(filter_tasks(tagged, today=TODAY, tags=["work", "urgent"])) == [1]


def test_ac_5_3_multiple_tags_match_any(tagged: list[Task]) -> None:
    assert ids(filter_tasks(tagged, today=TODAY, tags=["urgent", "home"], match="any")) == [1]


def test_ac_5_4_tag_filter_is_case_insensitive(tagged: list[Task]) -> None:
    assert ids(filter_tasks(tagged, today=TODAY, tags=["WORK"])) == [1, 2]


def test_ac_5_5_unknown_tag_returns_empty(tagged: list[Task]) -> None:
    assert filter_tasks(tagged, today=TODAY, tags=["nope"]) == []


def test_ac_5_6_status_filter_and_invalid_status(make_task: Callable[..., Task]) -> None:
    tasks = [make_task(id=1), make_task(id=2, status=Status.IN_PROGRESS)]
    assert ids(filter_tasks(tasks, today=TODAY, status="in_progress")) == [2]
    with pytest.raises(ValidationError):
        filter_tasks(tasks, today=TODAY, status="bogus")


def test_ac_5_7_filters_combine_with_and(make_task: Callable[..., Task]) -> None:
    tasks = [
        make_task(id=1, priority=Priority.HIGH, tags=("work",)),
        make_task(id=2, priority=Priority.HIGH, tags=("home",)),
        make_task(id=3, priority=Priority.LOW, tags=("work",)),
        make_task(id=4, priority=Priority.HIGH, tags=("work",), status=Status.COMPLETED),
    ]
    result = filter_tasks(tasks, today=TODAY, status="pending", priority="high", tags=["work"])
    assert ids(result) == [1]


def test_ac_5_8_overdue_filter(make_task: Callable[..., Task]) -> None:
    tasks = [
        make_task(id=1, due=date(2026, 11, 11)),
        make_task(id=2, due=date(2026, 11, 12)),
        make_task(id=3, due=date(2026, 11, 11), status=Status.COMPLETED),
        make_task(id=4),
    ]
    assert ids(filter_tasks(tasks, today=TODAY, overdue=True)) == [1]
    assert ids(filter_tasks(tasks, today=TODAY, overdue=False)) == [2, 3, 4]


def test_ac_5_9_invalid_match_rejected(tagged: list[Task]) -> None:
    with pytest.raises(ValidationError):
        filter_tasks(tagged, today=TODAY, match="some")


@pytest.fixture
def prioritised(make_task: Callable[..., Task]) -> list[Task]:
    return [
        make_task(id=1, priority=Priority.LOW),
        make_task(id=2, priority=Priority.HIGH),
        make_task(id=3, priority=Priority.MEDIUM),
        make_task(id=4, priority=Priority.HIGH),
    ]


def test_ac_7_1_default_is_priority_descending(prioritised: list[Task]) -> None:
    assert ids(sort_tasks(prioritised)) == [2, 4, 3, 1]


def test_ac_7_2_priority_ascending(prioritised: list[Task]) -> None:
    assert ids(sort_tasks(prioritised, key="priority", order="asc")) == [1, 3, 2, 4]


def test_ac_7_3_due_date_sort_puts_missing_last_in_both_orders(
    make_task: Callable[..., Task],
) -> None:
    tasks = [
        make_task(id=1, due=date(2026, 12, 1)),
        make_task(id=2),
        make_task(id=3, due=date(2026, 11, 15)),
    ]
    assert ids(sort_tasks(tasks, key="due_date", order="asc")) == [3, 1, 2]
    assert ids(sort_tasks(tasks, key="due_date", order="desc")) == [1, 3, 2]


def test_ac_7_5_invalid_sort_or_order_rejected(prioritised: list[Task]) -> None:
    with pytest.raises(ValidationError):
        sort_tasks(prioritised, key="colour")
    with pytest.raises(ValidationError):
        sort_tasks(prioritised, order="sideways")


def test_ac_7_6_sort_is_deterministic_with_id_tiebreak(prioritised: list[Task]) -> None:
    first = ids(sort_tasks(prioritised, key="priority", order="desc"))
    assert first == ids(sort_tasks(list(reversed(prioritised)), key="priority", order="desc"))


def test_created_at_and_id_sorting(make_task: Callable[..., Task]) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    tasks = [
        make_task(id=1, created=base + timedelta(days=2)),
        make_task(id=2, created=base),
    ]
    assert ids(sort_tasks(tasks, key="created_at")) == [2, 1]
    assert ids(sort_tasks(tasks, key="id", order="desc")) == [2, 1]


def test_ac_8_1_overdue_beats_higher_priority(make_task: Callable[..., Task]) -> None:
    tasks = [
        make_task(id=1, priority=Priority.LOW, due=date(2026, 11, 1)),
        make_task(id=2, priority=Priority.HIGH),
    ]
    assert select_next(tasks, TODAY) == tasks[0]


def test_ac_8_2_two_overdue_higher_priority_wins(make_task: Callable[..., Task]) -> None:
    tasks = [
        make_task(id=2, priority=Priority.MEDIUM, due=date(2026, 11, 1)),
        make_task(id=3, priority=Priority.HIGH, due=date(2026, 11, 1)),
    ]
    assert select_next(tasks, TODAY) == tasks[1]


def test_ac_8_3_nothing_actionable(make_task: Callable[..., Task]) -> None:
    assert select_next([], TODAY) is None
    assert select_next([make_task(status=Status.COMPLETED)], TODAY) is None


def test_ac_8_4_in_progress_beats_pending_when_otherwise_equal(
    make_task: Callable[..., Task],
) -> None:
    tasks = [make_task(id=1), make_task(id=2, status=Status.IN_PROGRESS)]
    assert select_next(tasks, TODAY) == tasks[1]
