"""Duration parsing: 'in N units' (DT-4) and bare durations for snooze / displacement."""

from __future__ import annotations

import re
from dataclasses import dataclass

NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}  # fmt: skip
UNITS = {
    "minute": "min", "minutes": "min", "min": "min", "mins": "min",
    "hour": "hour", "hours": "hour", "hr": "hour", "hrs": "hour",
    "day": "day", "days": "day", "week": "week", "weeks": "week",
    "month": "month", "months": "month",
}  # fmt: skip
MINUTES_PER = {"min": 1, "hour": 60, "day": 1440, "week": 10080}

_AMOUNT = r"(\d{1,3}|" + "|".join(NUMBER_WORDS) + r")"
_UNITS = "|".join(sorted(UNITS, key=len, reverse=True))
_RELATIVE = re.compile(rf"^in\s+{_AMOUNT}\s+({_UNITS})(?:\s+from now)?$")
_DURATION = re.compile(rf"^(?:for\s+|by\s+|back\s+|forward\s+|another\s+)*{_AMOUNT}\s*({_UNITS})$")


@dataclass(frozen=True)
class Amount:
    count: int
    unit: str  # min | hour | day | week | month


def _amount(count_text: str, unit_text: str) -> Amount:
    count = NUMBER_WORDS.get(count_text)
    return Amount(count if count is not None else int(count_text), UNITS[unit_text])


def parse_relative(normalized: str) -> Amount | None:
    """Match 'in 3 hours', 'in a week'... Returns None when the text is not of that form."""
    found = _RELATIVE.match(normalized)
    return _amount(found.group(1), found.group(2)) if found else None


def parse_duration_minutes(text: str) -> int | None:
    """Return whole minutes for '15 minutes', 'an hour', '2 days'. None if unparseable or zero/negative.

    Months are rejected (variable length); callers use ``parse_relative`` for calendar months.
    """
    normalized = " ".join(text.lower().split()).strip(".,!")
    if normalized in {"half an hour", "half hour"}:
        return 30
    found = _DURATION.match(normalized)
    if not found:
        return None
    amount = _amount(found.group(1), found.group(2))
    if amount.unit == "month" or amount.count <= 0:
        return None
    return amount.count * MINUTES_PER[amount.unit]
