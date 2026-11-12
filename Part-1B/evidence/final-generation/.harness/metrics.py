"""Aggregates per-turn facts into the spec section 9.3 metrics and applies the thresholds."""

from __future__ import annotations

import math
from typing import Any

from common import SUCCESS_TYPES


def _rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def wilson(successes: int, n: int, z: float = 1.96) -> list[float] | None:
    """95% Wilson score interval, reported next to every rate (spec 9.1)."""
    if n == 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)] if ordered else 0.0


def compute(turns: list[dict], cases: list[dict]) -> dict[str, dict[str, Any]]:
    """``turns``: records with `facts`, `layer1_ok`, `layer2`, `layer3` ; ``cases``: per-case summaries."""
    out: dict[str, dict[str, Any]] = {}

    def put(key: str, num: int | float, den: int, *, rate: bool = True) -> None:
        value = _rate(int(num), den) if rate else num
        out[key] = {"value": value, "n": den, "ci95": wilson(int(num), den) if rate and den else None}

    put("EVAL-1", sum(t["layer1_ok"] for t in turns), len(turns))
    dated = [
        t
        for t in turns
        if "reminder.due_at" in t["expected"].get("fields", {}) and t["facts"]["actual_type"] == t["expected_type"]
    ]
    put("EVAL-5", sum("reminder.due_at" not in t["facts"].get("bad_fields", []) for t in dated), len(dated))
    expecting_clar = [t for t in turns if t["expected_type"] == "clarification_needed"]
    put("EVAL-6r", sum(t["facts"].get("missing_recall_ok") is True for t in expecting_clar), len(expecting_clar))
    exact = [t for t in expecting_clar if t["facts"].get("missing_precision_ok") is not None]
    put("EVAL-6p", sum(t["facts"]["missing_precision_ok"] for t in exact), len(exact))
    complete = [t for t in turns if t["expected_type"] in SUCCESS_TYPES]
    put("EVAL-7", sum(t["facts"]["actual_type"] == "clarification_needed" for t in complete), len(complete))
    put("EVAL-8", sum(t["facts"]["actual_type"] in SUCCESS_TYPES for t in expecting_clar), len(expecting_clar))
    targeted = [t for t in turns if t["expected_type"] in {"reminder_rescheduled", "reminder_snoozed"}]
    put(
        "EVAL-9a",
        sum(
            t["response"]["type"] == t["expected_type"] and "reminder.id" not in t["facts"].get("bad_fields", [])
            for t in targeted
        ),
        len(targeted),
    )
    wrong = [
        t
        for t in turns
        if t["response"]["type"] in {"reminder_rescheduled", "reminder_snoozed"}
        and (t["expected_type"] != t["response"]["type"] or "reminder.id" in t["facts"].get("bad_fields", []))
    ]
    put("EVAL-9b", len(wrong), len(turns))
    put("EVAL-10", sum(any(f["check"] in {"INV-3", "INV-4"} for f in t["layer2"]) for t in turns), len(turns))
    adversarial = [c for c in cases if c["category"].startswith("adversarial")]
    put("EVAL-11", sum(not c["passed"] for c in adversarial), len(adversarial))
    put("EVAL-12", sum(any(f["check"] in {"INV-7", "INV-8"} for f in t["layer2"]) for t in turns), len(turns))
    out["EVAL-15"] = {"value": round(_p95([t["latency_ms"] for t in turns]), 3), "n": len(turns), "ci95": None}
    faults = [c for c in cases if c["category"].startswith("fault")]
    put("EVAL-17", sum(c["passed"] for c in faults), len(faults))
    return out


def judge(values: dict[str, dict[str, Any]], thresholds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for spec in thresholds:
        measured = values.get(spec["id"], {})
        value = measured.get("value")
        if value is None:
            status = "NOT_MEASURED"
        else:
            status = "PASS" if (value >= spec["value"] if spec["op"] == ">=" else value <= spec["value"]) else "FAIL"
        rows.append({**spec, "measured": value, "n": measured.get("n"), "ci95": measured.get("ci95"), "status": status})
    return rows
