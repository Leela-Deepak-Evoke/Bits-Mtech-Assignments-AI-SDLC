"""Sanitiser, stores, Anthropic payload privacy, CLI, and architecture rules."""

import json
import re
from pathlib import Path

import pytest

from reminder_agent.cli import main
from reminder_agent.errors import StorageError
from reminder_agent.llm.anthropic_client import AnthropicExtractor
from reminder_agent.llm.base import ReplayExtractor
from reminder_agent.models import Ctx, Reminder
from reminder_agent.repositories import JsonFileStore, MemoryStore
from reminder_agent.sanitize import sanitize_text

SRC = Path(__file__).resolve().parents[2] / "src" / "reminder_agent"


def _reminder(rid: str = "rem_aaaaaaaa") -> Reminder:
    created = "2026-11-12T05:00:00Z"
    data = {
        "id": rid, "title": "x", "due_at": "2026-11-13T09:00:00+05:30", "timezone": "Asia/Kolkata",
        "status": "scheduled", "snooze_count": 0, "created_at": created, "updated_at": created,
    }  # fmt: skip
    return Reminder.from_dict(data)


def test_sanitize_strips_hidden_characters_but_keeps_markup() -> None:
    assert sanitize_text("buy milk‮​  now\n") == "buy milk now"
    assert sanitize_text("<b>x</b>'; DROP TABLE t;--") == "<b>x</b>'; DROP TABLE t;--"
    assert sanitize_text("café ☕ 日本語") == "café ☕ 日本語"


def test_memory_store_commit_is_atomic_and_ids_never_reused() -> None:
    store = MemoryStore([_reminder()])
    with pytest.raises(StorageError):
        store.commit(add=_reminder("rem_aaaaaaaa"))
    assert len(store.list()) == 1


def test_json_store_round_trip_and_failed_write_leaves_file_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    store = JsonFileStore(path)
    store.commit(add=_reminder())
    before = path.read_bytes()
    assert JsonFileStore(path).snapshot() == store.snapshot()
    path.chmod(0o444)  # not enforced on every OS; the monkeypatch-free check below is the portable one
    blocker = tmp_path / "blocked"
    blocker.write_text("a file, not a directory")
    broken = JsonFileStore(blocker / "x.json")
    with pytest.raises(StorageError):
        broken.commit(add=_reminder("rem_bbbbbbbb"))
    assert broken.list() == []
    path.chmod(0o666)
    assert path.read_bytes() == before


def test_anthropic_request_has_no_tools_and_no_now(ctx: Ctx) -> None:
    request = AnthropicExtractor(client=object()).build_request("Remind me", ctx, ["t" * 500] * 30, None)
    blob = json.dumps(request)
    assert "tools" not in request and request["temperature"] == 0
    assert ctx.now.isoformat() not in blob and "2026-11-12" not in blob
    assert blob.count("t" * 80) >= 20 and "t" * 81 not in blob.replace("t" * 500, "")  # titles truncated, max 20 sent


def test_cli_json_output_and_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = "Remind me to call mom tomorrow at 5pm"
    spans = {"title": "call mom", "time": "tomorrow at 5pm", "duration": None, "target": None}
    gold = {"schema_version": "1.0", "intent": "create"} | {
        k: ({"text": v, "start": text.index(v), "end": text.index(v) + len(v)} if v else None) for k, v in spans.items()
    }
    code = main([text, "--json", "--data-file", str(tmp_path / "d.json")], extractor=ReplayExtractor({text: gold}))
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["type"] == "reminder_created"
    code = main(["   ", "--json", "--data-file", str(tmp_path / "d.json")], extractor=ReplayExtractor({}))
    assert code == 2 and json.loads(capsys.readouterr().out)["reason"] == "input_invalid"


def test_no_wall_clock_calls_outside_cli() -> None:
    bad = re.compile(r"datetime\.now|utcnow|time\.time\(|date\.today")
    offenders = [p.name for p in SRC.rglob("*.py") if p.name != "cli.py" and bad.search(p.read_text(encoding="utf-8"))]
    assert offenders == []


def test_layering_domain_modules_do_not_import_services() -> None:
    for name in ("models.py", "sanitize.py", "errors.py"):
        assert "reminder_agent.services" not in (SRC / name).read_text(encoding="utf-8")
    for path in (SRC / "resolver").glob("*.py"):
        assert "reminder_agent.services" not in path.read_text(encoding="utf-8")
