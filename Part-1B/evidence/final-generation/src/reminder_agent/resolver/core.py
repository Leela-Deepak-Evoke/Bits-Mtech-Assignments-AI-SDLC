"""Deterministic resolution of a time phrase into an instant (FR-3). No LLM, no wall-clock access."""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass, field

from reminder_agent.models import Ctx
from reminder_agent.resolver import clock, dates, durations
from reminder_agent.resolver.tz import local_to_aware

MIN_LEAD = dt.timedelta(seconds=60)
HORIZON = dt.timedelta(days=730)

PAST = "PAST"
OUT_OF_RANGE = "OUT_OF_RANGE"
MISSING_DATE = "MISSING_DATE"
VAGUE_DATE = dates.VAGUE
MISSING_MERIDIEM = clock.MERIDIEM_ISSUE
AMBIGUOUS_ORDER = dates.AMBIGUOUS_ORDER
BLOCKING = {VAGUE_DATE, MISSING_DATE, MISSING_MERIDIEM, AMBIGUOUS_ORDER}


@dataclass
class Resolution:
    """Outcome of resolving a phrase. ``instant`` is None when blocked by ``issues``."""

    instant: dt.datetime | None = None
    date: dt.date | None = None
    time: dt.time | None = None  # set only when the user stated a time explicitly
    assumptions: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def note(self, code: str | None) -> None:
        if code and code not in self.assumptions:
            self.assumptions.append(code)


def normalize(text: str) -> str:
    return " ".join(text.lower().split()).strip(".,!;")


def check_bounds(instant: dt.datetime, ctx: Ctx, *, explicit: bool = False) -> str | None:
    """DT-14 / DT-15 / INV-5. Returns an issue code or None."""
    if instant < ctx.now:
        return PAST if explicit else OUT_OF_RANGE
    if instant < ctx.now + MIN_LEAD or instant > ctx.now + HORIZON:
        return OUT_OF_RANGE
    return None


def add_months(day: dt.date, months: int) -> tuple[dt.date, bool]:
    """Calendar-month addition clamped to month end. Returns (date, clamped?)."""
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, min(day.day, last)), day.day > last


def _resolve_relative(amount: durations.Amount, ctx: Ctx) -> Resolution:
    res = Resolution(assumptions=["relative_to_now"])
    local = ctx.now_local
    if amount.unit in ("min", "hour"):
        minutes = amount.count * durations.MINUTES_PER[amount.unit]
        instant = ctx.now + dt.timedelta(minutes=minutes)
        res.instant = instant.astimezone(ctx.tz)
    else:
        if amount.unit == "month":
            target, clamped = add_months(local.date(), amount.count)
            res.note("month_end_clamped" if clamped else None)
        else:
            days = amount.count * (7 if amount.unit == "week" else 1)
            target = local.date() + dt.timedelta(days=days)
        res.instant, dst = local_to_aware(dt.datetime.combine(target, local.time().replace(microsecond=0)), ctx.tz)
        res.note(dst)
    return _finish(res, ctx, explicit=False)


def _finish(res: Resolution, ctx: Ctx, *, explicit: bool) -> Resolution:
    assert res.instant is not None  # noqa: S101 - internal contract
    res.date = res.instant.date()
    if bound := check_bounds(res.instant, ctx, explicit=explicit):
        res.issues.append(bound)
    return res


def _blocked(hit: dates.DateHit | None, ch: clock.ClockHit | None) -> list[str]:
    issues: list[str] = []
    if ch is not None and ch.issue:
        issues.append(clock.MERIDIEM_ISSUE if ch.issue == clock.MERIDIEM_ISSUE else VAGUE_DATE)
        if hit is None and ch.issue == clock.MERIDIEM_ISSUE:
            issues.append(MISSING_DATE)  # DT-11 cannot pick today/tomorrow without knowing am/pm
    if hit is not None and hit.issue:
        issues.append(hit.issue)
    return list(dict.fromkeys(issues))


def _time_of_day(ch: clock.ClockHit | None, res: Resolution) -> dt.time:
    if ch is None:
        res.note("default_time_0900")
        return dt.time(9)
    if ch.kind == "named":
        res.note("named_period_default")
    else:
        res.time = ch.time
    assert ch.time is not None  # noqa: S101
    return ch.time


def _calendar_date(hit: dates.DateHit, ctx: Ctx, at: dt.time) -> dt.date | None:
    local = ctx.now_local
    assert hit.month is not None and hit.day is not None  # noqa: S101
    years = [hit.year] if hit.year is not None else range(local.year, local.year + 5)
    for year in years:
        try:
            day = dt.date(year, hit.month, hit.day)
        except ValueError:
            continue
        if hit.year is not None:
            return day
        instant, _ = local_to_aware(dt.datetime.combine(day, at), ctx.tz)
        if instant >= ctx.now + MIN_LEAD:
            return day
    return None


def _weekday_date(hit: dates.DateHit, ctx: Ctx, at: dt.time) -> dt.date:
    today = ctx.now_local.date()
    assert hit.weekday is not None  # noqa: S101
    if hit.kind == "next_weekday":
        return today - dt.timedelta(days=today.weekday()) + dt.timedelta(days=7 + hit.weekday)
    for offset in range(8):
        day = today + dt.timedelta(days=offset)
        if day.weekday() == hit.weekday:
            instant, _ = local_to_aware(dt.datetime.combine(day, at), ctx.tz)
            if instant >= ctx.now + MIN_LEAD:
                return day
    return today + dt.timedelta(days=7)  # unreachable in practice; keeps the function total


def _pick_date(hit: dates.DateHit, ctx: Ctx, at: dt.time) -> dt.date | None:
    today = ctx.now_local.date()
    if hit.kind == "today":
        return today
    if hit.kind == "tomorrow":
        return today + dt.timedelta(days=1)
    if hit.kind == "dat":
        return today + dt.timedelta(days=2)
    if hit.kind == "calendar":
        return _calendar_date(hit, ctx, at)
    return _weekday_date(hit, ctx, at)


def _time_only(ch: clock.ClockHit, ctx: Ctx, res: Resolution) -> dt.date:
    """DT-11: today if still >= now+60s, else tomorrow (midnight always means the next calendar day)."""
    at = _time_of_day(ch, res)
    today = ctx.now_local.date()
    if ch.kind == "midnight":
        return today + dt.timedelta(days=1)
    instant, _ = local_to_aware(dt.datetime.combine(today, at), ctx.tz)
    if instant < ctx.now + MIN_LEAD:
        res.note("rolled_to_next_day")
        return today + dt.timedelta(days=1)
    return today


def resolve_time(text: str, ctx: Ctx) -> Resolution:
    """Resolve a time phrase relative to ``ctx``. Ambiguity yields ``issues`` instead of a guess."""
    normalized = normalize(text)
    amount = durations.parse_relative(normalized)
    if amount is not None:
        return _resolve_relative(amount, ctx)
    hit, rest = dates.find_date(normalized, ctx)
    ch = clock.find_clock(rest)
    res = Resolution()
    if hit is None and ch is None:
        res.issues.append(VAGUE_DATE)
        return res
    if blocked := _blocked(hit, ch):
        res.issues = blocked
        return res
    if hit is not None and hit.kind == "vague":
        res.issues.append(VAGUE_DATE)
        return res
    if hit is None:
        assert ch is not None  # noqa: S101 - both None was handled above
        day = _time_only(ch, ctx, res)
        at = ch.time
    else:
        at = _time_of_day(ch, res)
        day = _pick_date(hit, ctx, at)
        if day is None:
            res.issues.append(VAGUE_DATE)  # e.g. 30 Feb: cannot be scheduled, ask again
            return res
    assert at is not None  # noqa: S101
    res.instant, dst = local_to_aware(dt.datetime.combine(day, at), ctx.tz)
    res.note(dst)
    return _finish(res, ctx, explicit=hit is not None and hit.explicit)
