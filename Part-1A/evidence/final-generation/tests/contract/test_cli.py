import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from todo.interfaces.cli.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def data_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "cli.json"
    monkeypatch.setenv("TODO_DATA_FILE", str(path))
    return path


def invoke(*args: str):  # type: ignore[no-untyped-def]
    return runner.invoke(app, list(args))


COMMANDS = ["add", "list", "show", "update", "delete", "start", "complete", "reopen", "next"]


@pytest.mark.parametrize("command", COMMANDS)
def test_ac_10_1_every_command_has_help(command: str) -> None:
    result = invoke(command, "--help")
    assert result.exit_code == 0
    assert result.stdout.strip()


def test_ac_10_2_add_json() -> None:
    result = invoke("add", "Buy milk", "--priority", "high", "--tag", "home", "--json")
    assert result.exit_code == 0
    task = json.loads(result.stdout)
    assert (task["id"], task["title"], task["priority"], task["tags"]) == (
        1,
        "Buy milk",
        "high",
        ["home"],
    )
    assert task["status"] == "pending"


def test_ac_10_3_list_json_empty_and_populated() -> None:
    assert json.loads(invoke("list", "--json").stdout) == []
    invoke("add", "a")
    assert len(json.loads(invoke("list", "--json").stdout)) == 1


def test_ac_10_6_human_list_has_one_line_per_task() -> None:
    invoke("add", "Pay rent", "--tag", "home", "--due", "2000-01-01")
    invoke("add", "Read book")
    lines = invoke("list").stdout.strip().splitlines()
    assert len(lines) == 2
    assert "Pay rent" in lines[0] or "Pay rent" in lines[1]
    overdue_line = next(line for line in lines if "Pay rent" in line)
    assert "#home" in overdue_line
    assert "2000-01-01" in overdue_line
    assert "OVERDUE" in overdue_line


def test_cli_tag_filter_and_priority_sort() -> None:
    invoke("add", "low", "--priority", "low", "--tag", "x")
    invoke("add", "high", "--priority", "high", "--tag", "x")
    invoke("add", "untagged", "--priority", "high")
    titles = [t["title"] for t in json.loads(invoke("list", "--tag", "x", "--json").stdout)]
    assert titles == ["high", "low"]


def test_ac_6_7_shortcuts_and_exit_codes() -> None:
    invoke("add", "a")
    assert json.loads(invoke("start", "1", "--json").stdout)["status"] == "in_progress"
    assert json.loads(invoke("complete", "1", "--json").stdout)["status"] == "completed"
    assert json.loads(invoke("reopen", "1", "--json").stdout)["status"] == "pending"
    invalid = invoke("reopen", "1")
    assert invalid.exit_code == 4
    assert invalid.stdout == ""
    assert "error" in invalid.stderr


@pytest.mark.parametrize(
    ("args", "code"),
    [
        (("add", " "), 2),
        (("add", "x", "--priority", "urgent"), 2),
        (("add", "x", "--due", "2026-02-30"), 2),
        (("list", "--sort", "colour"), 2),
        (("list", "--match", "some"), 2),
        (("show", "999"), 3),
        (("start", "999"), 3),
        (("show", "abc"), 2),
    ],
)
def test_ac_10_4_and_10_5_exit_codes_and_stderr(args: tuple[str, ...], code: int) -> None:
    result = invoke(*args)
    assert result.exit_code == code
    assert result.stdout == ""


def test_ac_3_3_update_and_clear_due() -> None:
    invoke("add", "a", "--due", "2030-01-01", "--tag", "t")
    updated = json.loads(invoke("update", "1", "--clear-due", "--clear-tags", "--json").stdout)
    assert updated["due_date"] is None
    assert updated["tags"] == []
    assert invoke("update", "1").exit_code == 2


def test_ac_4_4_delete_requires_yes() -> None:
    invoke("add", "a")
    refused = invoke("delete", "1")
    assert refused.exit_code == 2
    assert invoke("show", "1").exit_code == 0
    assert invoke("delete", "1", "--yes").exit_code == 0
    assert invoke("show", "1").exit_code == 3


def test_ac_8_3_next_with_nothing_is_not_an_error() -> None:
    result = invoke("next")
    assert result.exit_code == 0
    assert "No actionable task" in result.stdout


def test_ac_9_6_corrupt_file_warns_on_stderr(data_path: Path) -> None:
    data_path.write_text("{broken")
    result = invoke("list")
    assert result.exit_code == 0
    assert "warning" in result.stderr


def test_nfr_5_unicode_round_trip() -> None:
    invoke("add", "café ✅ 日本語")
    assert json.loads(invoke("show", "1", "--json").stdout)["title"] == "café ✅ 日本語"
