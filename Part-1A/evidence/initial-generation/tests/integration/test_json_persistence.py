import json
import os
from pathlib import Path

import pytest

from conftest import FakeClock
from todo.app.config import Settings
from todo.app.container import build_service
from todo.domain.errors import StorageError, StorageFormatError
from todo.infrastructure import file_io, serialization
from todo.infrastructure.json_repository import JsonFileTaskRepository
from todo.repositories.base import Store


def make_service(path: Path, clock: FakeClock, warnings: list[str] | None = None):  # type: ignore[no-untyped-def]
    on_warning = warnings.append if warnings is not None else None
    return build_service(Settings(data_file=path), clock=clock, on_warning=on_warning)


def test_ac_9_2_missing_file_means_empty_store_and_no_file_created(data_file: Path) -> None:
    repo = JsonFileTaskRepository(data_file)
    assert repo.load_all() == Store(next_id=1, tasks=())
    assert not data_file.exists()


def test_ac_9_1_data_visible_to_a_new_instance(data_file: Path, clock: FakeClock) -> None:
    make_service(data_file, clock).add_task({"title": "persisted", "tags": ["a"]})
    again = make_service(data_file, clock)
    assert again.get_task(1).task.title == "persisted"


def test_ac_9_2_parent_directory_created_on_first_write(data_file: Path, clock: FakeClock) -> None:
    make_service(data_file, clock).add_task({"title": "x"})
    assert data_file.is_file()


def test_ac_9_4_file_format(data_file: Path, clock: FakeClock) -> None:
    make_service(data_file, clock).add_task({"title": "café ✅", "due_date": "2026-11-20"})
    text = data_file.read_text(encoding="utf-8")
    document = json.loads(text)
    assert document["version"] == 1
    assert document["next_id"] == 2
    assert "overdue" not in text
    assert "café ✅" in text
    assert text.startswith('{\n  "version"')
    assert document["tasks"][0]["created_at"].endswith("Z")


def test_ac_9_5_next_id_survives_restart(data_file: Path, clock: FakeClock) -> None:
    first = make_service(data_file, clock)
    first.add_task({"title": "a"})
    first.add_task({"title": "b"})
    first.delete_task(2)
    assert make_service(data_file, clock).add_task({"title": "c"}).task.id == 3


@pytest.mark.parametrize(
    "content",
    [b"", b"{not json", b'{"version": 1}', b'{"version": 1, "next_id": 1, "tasks": [{"id": 1}]}', b"\xff\xfe"],
)
def test_ac_9_6_corrupt_file_is_quarantined_not_deleted(
    data_file: Path, clock: FakeClock, content: bytes
) -> None:
    data_file.parent.mkdir(parents=True)
    data_file.write_bytes(content)
    warnings: list[str] = []
    service = make_service(data_file, clock, warnings)
    assert service.list_tasks() == []
    quarantined = list(data_file.parent.glob("todo_data.json.corrupt-*"))
    assert len(quarantined) == 1
    assert quarantined[0].read_bytes() == content
    assert len(warnings) == 1


def test_ac_9_7_newer_version_fails_and_file_untouched(data_file: Path, clock: FakeClock) -> None:
    data_file.parent.mkdir(parents=True)
    original = json.dumps({"version": 99, "next_id": 1, "tasks": []}).encode()
    data_file.write_bytes(original)
    with pytest.raises(StorageError):
        make_service(data_file, clock).list_tasks()
    assert data_file.read_bytes() == original
    assert not list(data_file.parent.glob("*.corrupt-*"))


def test_ac_9_3_failed_write_leaves_original_intact(
    data_file: Path, clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = make_service(data_file, clock)
    service.add_task({"title": "keep me"})
    before = data_file.read_bytes()

    def boom(*_: object, **__: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(file_io.os, "replace", boom)
    with pytest.raises(StorageError):
        service.add_task({"title": "lost"})
    monkeypatch.undo()
    assert data_file.read_bytes() == before
    assert [p.name for p in data_file.parent.iterdir()] == [data_file.name]


def test_transient_permission_error_is_retried(
    data_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"count": 0}
    real_replace = os.replace

    def flaky(source: object, target: object) -> None:
        calls["count"] += 1
        if calls["count"] < 3:
            raise PermissionError
        real_replace(source, target)  # type: ignore[arg-type]

    monkeypatch.setattr(file_io.os, "replace", flaky)
    file_io.atomic_write_text(data_file, "ok", delay=0)
    assert data_file.read_text() == "ok"
    assert calls["count"] == 3


def test_ac_9_8_unwritable_location_is_a_storage_error(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file")
    with pytest.raises(StorageError):
        file_io.atomic_write_text(blocker / "child" / "data.json", "x")


def test_ac_9_9_failed_mutation_does_not_touch_file(data_file: Path, clock: FakeClock) -> None:
    service = make_service(data_file, clock)
    service.add_task({"title": "a"})
    before = data_file.read_bytes()
    with pytest.raises(Exception):  # noqa: B017, PT011
        service.update_task(1, {"title": ""})
    with pytest.raises(Exception):  # noqa: B017, PT011
        service.change_status(1, "in_progress") and service.change_status(1, "in_progress")
    assert data_file.read_bytes() != before  # first valid transition changed it
    snapshot = data_file.read_bytes()
    with pytest.raises(Exception):  # noqa: B017, PT011
        service.get_task(42)
    assert data_file.read_bytes() == snapshot


def test_serialization_round_trip_and_validation(clock: FakeClock) -> None:
    service = build_service(Settings(data_file=Path("unused")), clock=clock)
    assert service is not None
    store = Store(next_id=1, tasks=())
    assert serialization.from_dict(serialization.to_dict(store)) == store
    for bad in (
        [],
        {"version": "1"},
        {"version": 1, "next_id": 1},
        {"version": 1, "next_id": 1, "tasks": [{"id": 1, "title": "x"}]},
        {"version": 0, "next_id": 1, "tasks": []},
    ):
        with pytest.raises(StorageFormatError):
            serialization.from_dict(bad)
