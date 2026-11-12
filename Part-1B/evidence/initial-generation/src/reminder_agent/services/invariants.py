"""Runtime invariant gate: a response failing any check is never returned (INV-1, INV-2, INV-5)."""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

from reminder_agent.contracts import response_errors
from reminder_agent.models import Ctx, parse_iso
from reminder_agent.resolver import check_bounds

REMINDER_TYPES = {"reminder_created", "reminder_rescheduled", "reminder_snoozed"}


def response_problems(response: dict[str, Any], ctx: Ctx) -> list[str]:
    """Return violated invariants ([] when the response may be returned)."""
    problems = [f"INV-1 {p}" for p in response_errors(response)]
    if problems or response.get("type") not in REMINDER_TYPES:
        return problems
    reminder = response["reminder"]
    due, utc = parse_iso(reminder["due_at"]), parse_iso(reminder["due_at_utc"])
    zone = ZoneInfo(reminder["timezone"])
    if due != utc or due.utcoffset() != due.astimezone(zone).utcoffset():
        problems.append("INV-2 offset/UTC inconsistency")
    if reminder["timezone"] != ctx.timezone:
        problems.append("INV-2 timezone differs from context")
    if check_bounds(utc, ctx):
        problems.append("INV-5 due time outside [now+60s, now+730d]")
    return problems
