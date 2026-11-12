"""Policy + mutation proposals for create / reschedule / snooze (FR-2, FR-4, FR-5, FR-6).

Every function is side-effect free: it returns a ``Result`` and the agent performs the single commit (INV-8).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from reminder_agent import resolver
from reminder_agent.models import Ctx, Reminder
from reminder_agent.repositories.memory import MemoryStore
from reminder_agent.resolver import Resolution
from reminder_agent.sanitize import sanitize_text
from reminder_agent.services import responses
from reminder_agent.services.extraction import Extracted
from reminder_agent.services.targets import Match, find_target

MAX_TITLE = 200
SNOOZE_DEFAULT_MIN = 10
SNOOZE_MAX_MIN = 7 * 24 * 60
SNOOZE_CAP = 20
_BLOCKER_FIELD = {
    resolver.VAGUE_DATE: "date",
    resolver.MISSING_DATE: "date",
    resolver.MISSING_MERIDIEM: "time_meridiem",
    resolver.AMBIGUOUS_ORDER: "date_order",
}


@dataclass
class Result:
    response: dict
    add: Reminder | None = None
    update: Reminder | None = None
    pending: Extracted | None = None  # set when the response is a clarification
    touched: str | None = None  # reminder id for 'it' resolution in later turns


def _blockers(res: Resolution | None) -> list[str]:
    return [] if res is None else list(dict.fromkeys(_BLOCKER_FIELD[i] for i in res.issues if i in _BLOCKER_FIELD))


def _refusal_reason(res: Resolution) -> str | None:
    if resolver.PAST in res.issues:
        return "past_time"
    return "out_of_range" if resolver.OUT_OF_RANGE in res.issues else None


def _partial(res: Resolution | None, title: str = "", target: str | None = None) -> dict[str, str]:
    partial: dict[str, str] = {}
    if title and len(title) <= MAX_TITLE:
        partial["title"] = title
    if res is not None and res.instant is not None and not res.issues:
        partial["date"] = res.instant.date().isoformat()
        if res.time is not None:
            partial["time"] = res.time.strftime("%H:%M")
    if target:
        partial["target"] = target
    return partial


def _clarify(ex: Extracted, intent: str, missing: list[str], partial: dict[str, str], round_: int,
             candidates: list[str] | None = None) -> Result:  # fmt: skip
    body = responses.clarification(intent, missing, partial, round_, candidates)
    return Result(body, pending=ex)


def create(ex: Extracted, ctx: Ctx, new_id: str, round_: int) -> Result:
    title = sanitize_text(ex.title or "")
    missing = [] if title else ["title"]
    res = None
    if ex.time is None:
        missing.append("date")
    else:
        res = resolver.resolve_time(ex.time, ctx)
        missing += _blockers(res)
    if missing:
        return _clarify(ex, "create", list(dict.fromkeys(missing)), _partial(res, title), round_)
    assert res is not None  # noqa: S101 - a missing time was reported above
    if len(title) > MAX_TITLE:
        return Result(responses.refused("input_invalid"))
    if reason := _refusal_reason(res):
        return Result(responses.refused(reason))
    assert res.instant is not None  # noqa: S101
    reminder = Reminder(new_id, title, res.instant, ctx.timezone, "scheduled", 0, ctx.now, ctx.now)
    return Result(responses.created(reminder, res.assumptions), add=reminder, touched=reminder.id)


def _locate(ex: Extracted, store: MemoryStore, last_touched: str | None) -> Match:
    return find_target(ex.target, store, last_touched)


def _target_gate(match: Match) -> Result | None:
    if match.kind == "none":
        return Result(responses.refused("reminder_not_found"))
    if match.kind == "one" and match.reminder is not None and match.reminder.status == "cancelled":
        return Result(responses.refused("invalid_state"))
    return None


def reschedule(ex: Extracted, ctx: Ctx, store: MemoryStore, last_touched: str | None, round_: int) -> Result:
    match = _locate(ex, store, last_touched)
    if gate := _target_gate(match):
        return gate
    res = resolver.resolve_time(ex.time, ctx) if ex.time else None
    missing = ["target"] if match.kind in {"many", "missing"} else []
    missing += _blockers(res)
    minutes = None
    if res is None:
        minutes = resolver.parse_duration_minutes(ex.duration) if ex.duration else None
        if not ex.duration:
            missing.append("date")  # neither a new time nor a displacement was given
        elif minutes is None:
            missing.append("duration")  # given but unusable (zero, negative, unparseable)
    target_id = match.reminder.id if match.reminder else None
    if missing:
        partial = _partial(res, target=target_id)
        return _clarify(ex, "reschedule", list(dict.fromkeys(missing)), partial, round_, match.candidates)
    previous = match.reminder
    assert previous is not None  # noqa: S101 - kind 'one' guaranteed by the checks above
    if res is not None:
        if reason := _refusal_reason(res):
            return Result(responses.refused(reason))
        assert res.instant is not None  # noqa: S101
        due, notes = res.instant, res.assumptions
    else:
        assert minutes is not None  # noqa: S101
        due = (previous.due_at + dt.timedelta(minutes=minutes)).astimezone(ctx.tz)
        notes = ["relative_to_previous_due"]
        if resolver.check_bounds(due, ctx):
            return Result(responses.refused("out_of_range"))
    updated = previous.with_changes(due_at=due, updated_at=ctx.now)
    return Result(responses.rescheduled(updated, previous, notes), update=updated, touched=updated.id)


def snooze(ex: Extracted, ctx: Ctx, store: MemoryStore, last_touched: str | None, round_: int) -> Result:
    if ex.time:  # 'snooze until 6pm' is an absolute move: AC-6.6
        return reschedule(ex, ctx, store, last_touched, round_)
    match = _locate(ex, store, last_touched)
    if gate := _target_gate(match):
        return gate
    notes: list[str] = []
    minutes: int | None = SNOOZE_DEFAULT_MIN
    if ex.duration:
        minutes = resolver.parse_duration_minutes(ex.duration)
    else:
        notes.append("default_snooze_10_min")
    missing = ["target"] if match.kind in {"many", "missing"} else []
    missing += ["duration"] if minutes is None else []
    if missing:
        target_id = match.reminder.id if match.reminder else None
        partial = _partial(None, target=target_id)
        return _clarify(ex, "snooze", missing, partial, round_, match.candidates)
    previous = match.reminder
    assert previous is not None and minutes is not None  # noqa: S101
    if minutes > SNOOZE_MAX_MIN:
        return Result(responses.refused("out_of_range"))
    if previous.snooze_count >= SNOOZE_CAP:
        return Result(responses.refused("snooze_limit_reached"))
    due = (max(ctx.now, previous.due_at) + dt.timedelta(minutes=minutes)).astimezone(ctx.tz)
    updated = previous.with_changes(due_at=due, snooze_count=previous.snooze_count + 1, updated_at=ctx.now)
    return Result(responses.snoozed(updated, previous, minutes, notes), update=updated, touched=updated.id)
