from datetime import UTC, date, datetime

import pytest

from todo.domain.errors import ValidationError
from todo.domain.rules import (
    build_task,
    normalize_description,
    normalize_tags,
    normalize_title,
    parse_due_date,
    parse_priority,
)
from todo.domain.task import Priority, Status

NOW = datetime(2026, 11, 12, 9, 0, 0, tzinfo=UTC)


@pytest.mark.parametrize("bad", ["", "   ", "\t\n"])
def test_ac_1_2_empty_or_blank_title_rejected(bad: str) -> None:
    with pytest.raises(ValidationError):
        normalize_title(bad)


def test_ac_1_3_title_length_boundary() -> None:
    assert normalize_title("a" * 200) == "a" * 200
    with pytest.raises(ValidationError):
        normalize_title("a" * 201)


def test_ac_1_4_title_is_trimmed() -> None:
    assert normalize_title("  Buy milk  ") == "Buy milk"


@pytest.mark.parametrize("title", ["café ✅", "日本語"])
def test_nfr_5_unicode_title_preserved(title: str) -> None:
    assert normalize_title(title) == title


def test_ac_1_5_tags_lowercased_trimmed_deduplicated() -> None:
    assert normalize_tags(["Work", "work", " Home "]) == ("work", "home")


def test_ac_1_6_tag_count_boundary() -> None:
    assert len(normalize_tags([f"t{i}" for i in range(10)])) == 10
    with pytest.raises(ValidationError):
        normalize_tags([f"t{i}" for i in range(11)])


def test_ac_1_6_tag_length_boundary() -> None:
    assert normalize_tags(["a" * 30]) == ("a" * 30,)
    with pytest.raises(ValidationError):
        normalize_tags(["a" * 31])


@pytest.mark.parametrize("bad", ["a b", "#x", "", "-lead", "émoji"])
def test_ac_1_6_invalid_tag_characters_rejected(bad: str) -> None:
    with pytest.raises(ValidationError):
        normalize_tags([bad])


def test_tags_must_be_a_list_not_a_string() -> None:
    with pytest.raises(ValidationError):
        normalize_tags("work")


@pytest.mark.parametrize("value", ["urgent", "", None, 3])
def test_ac_1_7_invalid_priority_rejected(value: object) -> None:
    with pytest.raises(ValidationError):
        parse_priority(value)


def test_priority_parsing_is_case_insensitive() -> None:
    assert parse_priority("HIGH") is Priority.HIGH


@pytest.mark.parametrize("bad", ["2026-02-30", "12/11/2026", "20261112", "2026-1-1", "tomorrow"])
def test_ac_1_8_invalid_due_date_rejected(bad: str) -> None:
    with pytest.raises(ValidationError):
        parse_due_date(bad)


@pytest.mark.parametrize("good", ["2020-01-01", "9999-12-31"])
def test_ac_1_8_past_and_far_future_due_dates_accepted(good: str) -> None:
    assert parse_due_date(good) == date.fromisoformat(good)


def test_description_length_boundary() -> None:
    assert normalize_description("x" * 2000)
    with pytest.raises(ValidationError):
        normalize_description("x" * 2001)


def test_ac_1_1_build_task_defaults() -> None:
    task = build_task(1, NOW, {"title": "Buy milk"})
    assert task.status is Status.PENDING
    assert task.priority is Priority.MEDIUM
    assert task.tags == ()
    assert task.description == ""
    assert task.due_date is None
    assert task.completed_at is None
    assert task.created_at == task.updated_at == NOW


def test_ac_1_9_build_task_uses_given_id() -> None:
    assert build_task(7, NOW, {"title": "x"}).id == 7


@pytest.mark.parametrize("field", ["id", "status", "created_at", "updated_at", "completed_at"])
def test_ac_1_10_system_fields_rejected_on_create(field: str) -> None:
    with pytest.raises(ValidationError):
        build_task(1, NOW, {"title": "x", field: "anything"})


def test_title_is_required() -> None:
    with pytest.raises(ValidationError):
        build_task(1, NOW, {})
