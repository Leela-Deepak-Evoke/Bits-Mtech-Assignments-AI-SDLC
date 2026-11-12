"""LAYER 2 - structural invariants (spec section 5), re-implemented independently of the agent.

Each check returns Findings; an empty list means the invariant held for that turn.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from typing import Any
from zoneinfo import ZoneInfo

from common import HIDDEN_CHARS, LEAK_PATTERNS, ROOT, SUCCESS_TYPES, Finding, parse_iso

LAYER = 2
MIN_LEAD = dt.timedelta(seconds=60)
HORIZON = dt.timedelta(days=730)
ASSUMPTION_ENUM = {
    "default_time_0900", "named_period_default", "rolled_to_next_day", "relative_to_now",
    "relative_to_previous_due", "default_snooze_10_min", "month_end_clamped",
    "dst_gap_shifted_forward", "dst_overlap_first_occurrence", "timezone_from_context",
}  # fmt: skip


def _f(check: str, detail: str) -> Finding:
    return Finding(LAYER, check, detail)


def _collapse(text: str) -> str:
    text = unicodedata.normalize("NFC", re.sub(r"[\t\n\r\x0b\x0c]+", " ", text))
    return re.sub(r" {2,}", " ", HIDDEN_CHARS.sub("", text)).strip()


def inv2_offsets(resp: dict, ctx: dict) -> list[Finding]:
    rem = resp.get("reminder")
    if resp["type"] not in SUCCESS_TYPES or not rem:
        return []
    out = []
    due, utc = parse_iso(rem["due_at"]), parse_iso(rem["due_at_utc"])
    zone = ZoneInfo(rem["timezone"])
    if due != utc:
        out.append(_f("INV-2", "due_at and due_at_utc are different instants"))
    if due.utcoffset() != utc.astimezone(zone).utcoffset():
        out.append(_f("INV-2", f"offset {due.utcoffset()} is not the {rem['timezone']} offset at that instant"))
    if rem["timezone"] != ctx["timezone"]:
        out.append(_f("INV-2", "reminder timezone differs from ctx timezone"))
    return out


def inv3_spans(message: str, returned: list[Any]) -> list[Finding]:
    out = []
    for raw in returned:
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            continue  # malformed output is Layer 1's / the retry path's concern
        if not isinstance(data, dict):
            continue
        for name in ("title", "time", "duration", "target"):
            span = data.get(name)
            if isinstance(span, dict) and message[span.get("start", 0) : span.get("end", 0)] != span.get("text"):
                out.append(_f("INV-3", f"{name} span does not match message[start:end]"))
    return out


def inv4_provenance(resp: dict, dialogue: list[str]) -> list[Finding]:
    """Title must be a substring of ONE user message of the current clarification dialogue (spec v1.0.1)."""
    rem = resp.get("reminder")
    if resp["type"] != "reminder_created" or not rem:
        return []
    if any(rem["title"] in _collapse(message) for message in dialogue):
        return []
    return [_f("INV-4", "title is not a substring of any message in this dialogue")]


def inv5_future(resp: dict, ctx: dict) -> list[Finding]:
    rem = resp.get("reminder")
    if resp["type"] not in SUCCESS_TYPES or not rem:
        return []
    now, due = parse_iso(ctx["now"]), parse_iso(rem["due_at_utc"])
    if due < now + MIN_LEAD or due > now + HORIZON:
        return [_f("INV-5", f"due {rem['due_at_utc']} outside [now+60s, now+730d]")]
    return []


def inv6_bounds(resp: dict) -> list[Finding]:
    out = []
    if resp["type"] == "clarification_needed" and not 1 <= resp["round"] <= 3:
        out.append(_f("INV-6", "round outside 1..3"))
    rem = resp.get("reminder")
    if rem and not 0 <= rem["snooze_count"] <= 20:
        out.append(_f("INV-6", "snooze_count outside 0..20"))
    if resp["type"] == "reminder_snoozed" and not 1 <= resp["snooze_minutes"] <= 10080:
        out.append(_f("INV-6", "snooze_minutes outside 1..10080"))
    return out


def inv7_8_9_12_store(resp: dict, before: list[dict], after: list[dict]) -> list[Finding]:
    """INV-7 cardinality, INV-8 no side effect on non-success, INV-9 identity, INV-12 ids."""
    b, a = {r["id"]: r for r in before}, {r["id"]: r for r in after}
    out = []
    if len(a) != len(after) or not set(b) <= set(a):
        out.append(_f("INV-12", "duplicate or vanished reminder id"))
    kind = resp["type"]
    changed = [i for i in b if i in a and a[i] != b[i]]
    added = sorted(set(a) - set(b))
    if kind == "reminder_created":
        rid = resp["reminder"]["id"]
        if added != [rid] or changed:
            out.append(_f("INV-7", f"created: added={added} changed={changed}"))
        elif a[rid] != resp["reminder"]:
            out.append(_f("INV-7", "stored reminder differs from the one returned"))
    elif kind in {"reminder_rescheduled", "reminder_snoozed"}:
        rid = resp["reminder"]["id"]
        if added or changed != [rid]:
            out.append(_f("INV-7", f"{kind}: added={added} changed={changed}"))
        else:
            out += _identity(resp, b[rid], a[rid])
    elif added or changed or before != after:
        out.append(_f("INV-8", f"{kind} changed the store: added={added} changed={changed}"))
    return out


def _identity(resp: dict, old: dict, new: dict) -> list[Finding]:
    out = []
    for key in ("id", "title", "created_at", "timezone"):
        if old[key] != new[key]:
            out.append(_f("INV-9", f"{key} changed"))
    if parse_iso(new["updated_at"]) <= parse_iso(old["updated_at"]):
        out.append(_f("INV-9", "updated_at did not increase"))
    if parse_iso(resp["previous_due_at"]) != parse_iso(old["due_at"]):
        out.append(_f("INV-9", "previous_due_at differs from stored due_at before the call"))
    if resp["type"] == "reminder_snoozed" and new["snooze_count"] != old["snooze_count"] + 1:
        out.append(_f("INV-9", "snooze_count did not increase by exactly 1"))
    if resp["type"] == "reminder_rescheduled" and new["snooze_count"] != old["snooze_count"]:
        out.append(_f("INV-9", "reschedule changed snooze_count"))
    return out


def inv10_assumptions(resp: dict, ctx: dict) -> list[Finding]:
    codes = resp.get("assumptions")
    if codes is None:
        return []
    out = []
    if not set(codes) <= ASSUMPTION_ENUM:
        out.append(_f("INV-10", "unknown assumption code"))
    rem = resp["reminder"]
    due_local = parse_iso(rem["due_at"])
    now_local = parse_iso(ctx["now"]).astimezone(ZoneInfo(ctx["timezone"]))
    rules = {
        "default_time_0900": due_local.time() == dt.time(9),
        "rolled_to_next_day": due_local.date() > now_local.date(),
        "default_snooze_10_min": resp["type"] == "reminder_snoozed" and resp.get("snooze_minutes") == 10,
        "relative_to_previous_due": resp["type"] == "reminder_rescheduled",
        "month_end_clamped": "relative_to_now" in codes,
    }
    out += [
        _f("INV-10", f"assumption '{c}' is not supported by the response") for c in codes if c in rules and not rules[c]
    ]
    return out


def inv11_clarification(resp: dict) -> list[Finding]:
    if resp["type"] != "clarification_needed":
        return []
    out = []
    q = resp["question"]
    if q.count("?") != 1 or not q.endswith("?"):
        out.append(_f("INV-11", "question must contain exactly one '?', at the end"))
    if len(set(resp["missing_fields"])) != len(resp["missing_fields"]) or not resp["missing_fields"]:
        out.append(_f("INV-11", "missing_fields empty or not unique"))
    if resp.get("candidates") and "target" not in resp["missing_fields"]:
        out.append(_f("INV-11", "candidates present although target is not missing"))
    return out


def global_output_hygiene(resp: dict) -> list[Finding]:
    """SAF-6 (no hidden characters) and SAF-7 (no leaks) over the whole serialised response."""
    blob = json.dumps(resp, ensure_ascii=False)
    out = []
    if HIDDEN_CHARS.search(blob):
        out.append(_f("SAF-6", "control/bidi/zero-width character in response"))
    for pattern in LEAK_PATTERNS:
        if pattern.search(blob):
            out.append(_f("SAF-7", f"response matches leak pattern /{pattern.pattern}/"))
    return out


def inv13_clock_sourcing() -> list[Finding]:
    """Static scan: wall-clock calls are only allowed in the CLI, the one place real time enters."""
    bad = re.compile(r"datetime\.now|utcnow|time\.time\(|date\.today")
    out = []
    for path in (ROOT / "src").rglob("*.py"):
        if path.name == "cli.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if bad.search(line):
                out.append(_f("INV-13", f"{path.relative_to(ROOT)}:{number} reads the wall clock"))
    return out


def check_turn(rec: dict) -> list[Finding]:
    resp, ctx = rec["response"], rec["ctx"]
    found: list[Finding] = []
    for fn in (inv2_offsets, inv5_future, inv10_assumptions):
        found += fn(resp, ctx)
    found += inv3_spans(rec["guarded_message"], rec["extractions"]) + inv4_provenance(resp, rec["dialogue_messages"])
    found += inv6_bounds(resp) + inv11_clarification(resp) + global_output_hygiene(resp)
    found += inv7_8_9_12_store(resp, rec["store_before"], rec["store_after"])
    return found
