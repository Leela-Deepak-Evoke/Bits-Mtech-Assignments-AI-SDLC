"""FR-3 / DT-1..DT-16 on the fixture clock. Table-driven; each row is (phrase, expected local time | issue)."""

import pytest

from reminder_agent import resolver
from reminder_agent.models import Ctx

OK = [
    ("tomorrow at 5pm", "2026-11-13T17:00:00+05:30", []),
    ("tomorrow at 5:30 pm", "2026-11-13T17:30:00+05:30", []),
    ("day after tomorrow at 14:30", "2026-11-14T14:30:00+05:30", []),
    ("on 1 Dec 2026 at 14:30", "2026-12-01T14:30:00+05:30", []),
    ("Dec 1st 2026 at 9am", "2026-12-01T09:00:00+05:30", []),
    ("in 3 hours", "2026-11-12T13:30:00+05:30", ["relative_to_now"]),
    ("in a week", "2026-11-19T10:30:00+05:30", ["relative_to_now"]),
    ("next Friday", "2026-11-20T09:00:00+05:30", ["default_time_0900"]),
    ("Friday", "2026-11-13T09:00:00+05:30", ["default_time_0900"]),
    ("Thursday at 5pm", "2026-11-12T17:00:00+05:30", []),
    ("Thursday at 9am", "2026-11-19T09:00:00+05:30", []),
    ("at 9am", "2026-11-13T09:00:00+05:30", ["rolled_to_next_day"]),
    ("at 11am", "2026-11-12T11:00:00+05:30", []),
    ("at noon", "2026-11-13T12:00:00+05:30", ["rolled_to_next_day"]),
    ("tomorrow morning", "2026-11-13T09:00:00+05:30", ["named_period_default"]),
    ("tonight", "2026-11-12T20:00:00+05:30", ["named_period_default"]),
    ("on 13/04/2027 at 9am", "2027-04-13T09:00:00+05:30", []),
    ("on 03/04/2027 at 9am", "2027-04-03T09:00:00+05:30", []),  # DMY configured
    ("on 1 jan", "2027-01-01T09:00:00+05:30", ["default_time_0900"]),  # no year -> next occurrence
    ("in 1 minute", "2026-11-12T10:31:00+05:30", ["relative_to_now"]),  # exactly now+60s is allowed
    ("on 2028-11-11 at 10:30", "2028-11-11T10:30:00+05:30", []),  # exactly now+730d is allowed
]
BLOCKED = [
    ("at 5", {resolver.MISSING_MERIDIEM, resolver.MISSING_DATE}),
    ("tomorrow at 5", {resolver.MISSING_MERIDIEM}),
    ("next week", {resolver.VAGUE_DATE}),
    ("sometime", {resolver.VAGUE_DATE}),
    ("gibberish words", {resolver.VAGUE_DATE}),
    ("on 30 feb 2027", {resolver.VAGUE_DATE}),
    ("on 2020-01-01 at 9am", {resolver.PAST}),
    ("on 2028-11-12 at 10:30", {resolver.OUT_OF_RANGE}),
    ("in 30 seconds", {resolver.VAGUE_DATE}),
]


@pytest.mark.parametrize(("phrase", "expected", "assumptions"), OK)
def test_resolves(ctx: Ctx, phrase: str, expected: str, assumptions: list[str]) -> None:
    res = resolver.resolve_time(phrase, ctx)
    assert res.issues == []
    assert res.instant is not None and res.instant.isoformat() == expected
    assert sorted(res.assumptions) == sorted(assumptions)


@pytest.mark.parametrize(("phrase", "issues"), BLOCKED)
def test_blocked(ctx: Ctx, phrase: str, issues: set[str]) -> None:
    assert set(resolver.resolve_time(phrase, ctx).issues) == issues


def test_numeric_date_needs_order_when_unset(ctx: Ctx) -> None:
    unset = Ctx(ctx.now, ctx.timezone, "unset")
    assert resolver.resolve_time("on 03/04/2027", unset).issues == [resolver.AMBIGUOUS_ORDER]
    assert resolver.resolve_time("on 13/04/2027 at 9am", unset).issues == []


def test_month_end_clamp() -> None:
    ctx = Ctx.from_dict({"now": "2027-01-31T10:00:00+05:30", "timezone": "Asia/Kolkata"})
    res = resolver.resolve_time("in 1 month", ctx)
    assert res.instant is not None and res.instant.date().isoformat() == "2027-02-28"
    assert "month_end_clamped" in res.assumptions


def test_dst_gap_and_overlap() -> None:
    gap = Ctx.from_dict({"now": "2027-03-13T12:00:00-05:00", "timezone": "America/New_York"})
    res = resolver.resolve_time("tomorrow at 2:30am", gap)
    assert res.instant is not None and res.instant.isoformat() == "2027-03-14T03:30:00-04:00"
    assert res.assumptions == ["dst_gap_shifted_forward"]
    overlap = Ctx.from_dict({"now": "2027-11-06T12:00:00-04:00", "timezone": "America/New_York"})
    res = resolver.resolve_time("tomorrow at 1:30am", overlap)
    assert res.instant is not None and res.instant.isoformat() == "2027-11-07T01:30:00-04:00"  # first occurrence
    assert res.assumptions == ["dst_overlap_first_occurrence"]


@pytest.mark.parametrize(("text", "minutes"), [("15 minutes", 15), ("an hour", 60), ("2 days", 2880), ("0 minutes", None), ("-5 minutes", None), ("soon", None)])
def test_duration_minutes(text: str, minutes: int | None) -> None:
    assert resolver.parse_duration_minutes(text) == minutes
