"""Time-of-day recognition (DT-7, DT-8, DT-9). Pure string -> ClockHit."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

MERIDIEM_ISSUE = "MISSING_TIME_MERIDIEM"
INVALID = "VAGUE_DATE"

NAMED_PERIODS = {
    "morning": dt.time(9), "afternoon": dt.time(14), "evening": dt.time(18),
    "tonight": dt.time(20), "eod": dt.time(17), "end of day": dt.time(17),
}  # fmt: skip

_AMPM = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\b\.?")
_H24 = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
_NAMED = re.compile(r"\b(morning|afternoon|evening|tonight|eod|end of day)\b")
_BARE = re.compile(r"\bat\s+(\d{1,2})\b(?!\s*:)")


@dataclass(frozen=True)
class ClockHit:
    """kind: explicit | noon | midnight | named. ``issue`` is set when the hour is am/pm-ambiguous."""

    time: dt.time | None
    kind: str
    issue: str | None = None


def find_clock(text: str) -> ClockHit | None:
    """Find the time-of-day phrase in (already date-stripped) normalised text."""
    if re.search(r"\bnoon\b", text):
        return ClockHit(dt.time(12), "noon")
    if re.search(r"\bmidnight\b", text):
        return ClockHit(dt.time(0), "midnight")
    if found := _AMPM.search(text):
        hour, minute = int(found[1]), int(found[2] or 0)
        if not 1 <= hour <= 12:
            return ClockHit(None, "explicit", INVALID)
        hour = hour % 12 + (12 if found[3] == "p" else 0)
        return ClockHit(dt.time(hour, minute), "explicit")
    if found := _H24.search(text):
        return ClockHit(dt.time(int(found[1]), int(found[2])), "explicit")
    if found := _BARE.search(text):
        return _bare_hour(int(found[1]))
    if found := _NAMED.search(text):
        return ClockHit(NAMED_PERIODS[found[1]], "named")
    return None


def _bare_hour(hour: int) -> ClockHit:
    if 13 <= hour <= 23 or hour == 0:
        return ClockHit(dt.time(hour), "explicit")
    if 1 <= hour <= 12:
        return ClockHit(None, "explicit", MERIDIEM_ISSUE)
    return ClockHit(None, "explicit", INVALID)
