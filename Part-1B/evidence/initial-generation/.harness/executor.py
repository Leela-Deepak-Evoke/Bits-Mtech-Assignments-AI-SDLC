"""Runs dataset cases through the real agent (replay mode) and collects per-turn records."""

from __future__ import annotations

import sys
import time
import unicodedata
from typing import Any

from common import ROOT

sys.path.insert(0, str(ROOT / "src"))

from reminder_agent.errors import StorageError  # noqa: E402
from reminder_agent.llm.base import ReplayExtractor  # noqa: E402
from reminder_agent.models import Ctx, Reminder  # noqa: E402
from reminder_agent.repositories.memory import MemoryStore  # noqa: E402
from reminder_agent.services.agent import ReminderAgent  # noqa: E402


class FailingStore(MemoryStore):
    """Fault injection: every commit fails, as a full disk would (F-03)."""

    def _persist(self, items: dict[str, Reminder]) -> None:  # noqa: ARG002
        raise StorageError("injected write failure")


def _ids() -> Any:  # noqa: ANN401
    counter = iter(range(1, 10_000))
    return lambda: f"rem_new{next(counter):05d}"


def run_case(case: dict, dataset: dict) -> list[dict]:
    """Execute every turn of ``case``; return one record per turn."""
    ctx_data = dataset["default_ctx"] if case["ctx"] == "default" else case["ctx"]
    ctx = Ctx.from_dict(ctx_data)
    fault = case.get("fault") or {}
    reminders = [Reminder.from_dict(d) for d in dataset["store_fixtures"][case["store"]]]
    store_cls = FailingStore if fault.get("target") == "store" else MemoryStore
    store = store_cls(reminders)
    recorded = {t["message"]: t["gold_extraction"] for t in case["turns"] if t["gold_extraction"]}
    llm_fault = fault if fault.get("target") == "llm" else None
    extractor = ReplayExtractor(recorded, llm_fault)
    agent = ReminderAgent(extractor, store, _ids())
    records = []
    for index, turn in enumerate(case["turns"]):
        before, calls_before, returned_before = store.snapshot(), extractor.calls, len(extractor.returned)
        started = time.perf_counter()
        response = agent.handle(case["id"], turn["message"], ctx)
        elapsed_ms = (time.perf_counter() - started) * 1000
        records.append(
            {
                "case_id": case["id"], "turn": index, "message": turn["message"],
                "guarded_message": unicodedata.normalize("NFC", turn["message"]).strip(),
                "ctx": ctx_data, "expected": turn["expected"], "max_llm_calls": turn["max_llm_calls"],
                "response": response, "store_before": before, "store_after": store.snapshot(),
                "llm_calls": extractor.calls - calls_before, "extractions": extractor.returned[returned_before:],
                "latency_ms": round(elapsed_ms, 3),
            }
        )
    return records
