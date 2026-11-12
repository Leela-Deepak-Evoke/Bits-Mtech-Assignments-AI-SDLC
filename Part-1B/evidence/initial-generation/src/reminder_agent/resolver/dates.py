"""Date-phrase recognition (DT-1, 2, 3, 5, 6, 16). Pure string -> DateHit; no clock access."""

from __future__ import annotations

import re
from dataclasses import dataclass

from reminder_agent.models import Ctx

AMBIGUOUS_ORDER = "AMBIGUOUS_DATE_ORDER"
VAGUE = "VAGUE_DATE"

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}  # fmt: skip
WEEKDAYS = {
    "mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1, "wed": 2, "wednesday": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5, "sun": 6, "sunday": 6,
}  # fmt: skip

_MONTH = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b"
_WEEKDAY = r"(" + "|".join(sorted(WEEKDAYS, key=len, reverse=True)) + r")\b"
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_NUMERIC = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b")
_DAY_MONTH = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTH}\.?(?:,?\s+(\d{{4}}))?\b")
_MONTH_DAY = re.compile(rf"\b{_MONTH}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(\d{{4}})\b)?")
_DAY_AFTER = re.compile(r"\bday after tomorrow\b")
_TOMORROW = re.compile(r"\btomorrow\b")
_TODAY = re.compile(r"\b(?:today|tonight|this (?:morning|afternoon|evening))\b")
_NEXT_WEEKDAY = re.compile(rf"\bnext\s+{_WEEKDAY}")
_WEEKDAY_ONLY = re.compile(rf"\b(?:this\s+|on\s+)?{_WEEKDAY}")
_VAGUE = re.compile(r"\b(?:next|this coming)\s+(?:week|month|year)\b|\b(?:sometime|soon|later|eventually)\b")


@dataclass(frozen=True)
class DateHit:
    """kind: today | tomorrow | dat | weekday | next_weekday | calendar | vague."""

    kind: str
    weekday: int | None = None
    year: int | None = None
    month: int | None = None
    day: int | None = None
    issue: str | None = None

    @property
    def explicit(self) -> bool:
        """An explicit date that, if already past, is refused (DT-14) rather than rolled forward."""
        return self.kind == "today" or (self.kind == "calendar" and self.year is not None)


def _cut(text: str, found: re.Match[str]) -> str:
    return (text[: found.start()] + " " + text[found.end() :]).strip()


def _calendar(year: int | None, month: int, day: int) -> DateHit:
    return DateHit("calendar", year=year, month=month, day=day)


def _numeric(found: re.Match[str], ctx: Ctx) -> DateHit:
    first, second, year = int(found.group(1)), int(found.group(2)), int(found.group(3))
    if first > 12 or first == second:
        return _calendar(year, second, first)
    if second > 12:
        return _calendar(year, first, second)
    if ctx.date_order == "DMY":
        return _calendar(year, second, first)
    if ctx.date_order == "MDY":
        return _calendar(year, first, second)
    return DateHit("calendar", issue=AMBIGUOUS_ORDER)


def find_date(text: str, ctx: Ctx) -> tuple[DateHit | None, str]:
    """Find the first date phrase in normalised ``text``. Returns (hit | None, remaining text)."""
    if found := _ISO.search(text):
        return _calendar(int(found[1]), int(found[2]), int(found[3])), _cut(text, found)
    if found := _NUMERIC.search(text):
        return _numeric(found, ctx), _cut(text, found)
    if found := _DAY_MONTH.search(text):
        year = int(found[3]) if found[3] else None
        return _calendar(year, MONTHS[found[2][:3]], int(found[1])), _cut(text, found)
    if found := _MONTH_DAY.search(text):
        year = int(found[3]) if found[3] else None
        return _calendar(year, MONTHS[found[1][:3]], int(found[2])), _cut(text, found)
    return _find_keyword(text)


def _find_keyword(text: str) -> tuple[DateHit | None, str]:
    for pattern, kind in ((_DAY_AFTER, "dat"), (_TOMORROW, "tomorrow")):
        if found := pattern.search(text):
            return DateHit(kind), _cut(text, found)
    if found := _VAGUE.search(text):
        return DateHit("vague", issue=VAGUE), _cut(text, found)
    if found := _NEXT_WEEKDAY.search(text):
        return DateHit("next_weekday", weekday=WEEKDAYS[found[1]]), _cut(text, found)
    if found := _TODAY.search(text):
        # 'tonight' / 'this evening' keep their word for the clock stage; only the date is consumed.
        word = found.group(0)
        remaining = text if word != "today" else _cut(text, found)
        return DateHit("today"), remaining
    if found := _WEEKDAY_ONLY.search(text):
        return DateHit("weekday", weekday=WEEKDAYS[found[1]]), _cut(text, found)
    return None, text
