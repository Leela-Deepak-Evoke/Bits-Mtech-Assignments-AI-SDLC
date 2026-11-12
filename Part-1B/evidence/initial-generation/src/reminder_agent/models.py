"""Core value types: call context and Reminder."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from typing import Any
from zoneinfo import ZoneInfo

UTC = dt.timezone.utc  # noqa: UP017 - explicit for readability


def fmt_utc(moment: dt.datetime) -> str:
    """Format an aware datetime as UTC ISO-8601 with a ``Z`` suffix (fraction only when non-zero)."""
    utc = moment.astimezone(UTC)
    fraction = f".{utc.microsecond:06d}" if utc.microsecond else ""
    return utc.strftime("%Y-%m-%dT%H:%M:%S") + fraction + "Z"


def parse_iso(text: str) -> dt.datetime:
    """Parse an ISO-8601 string with offset or ``Z`` into an aware datetime."""
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


@dataclass(frozen=True)
class Ctx:
    """Per-call context. ``now`` is the ONLY time source for the whole pipeline (INV-13)."""

    now: dt.datetime
    timezone: str
    date_order: str = "DMY"

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def now_local(self) -> dt.datetime:
        return self.now.astimezone(self.tz)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ctx:
        return cls(parse_iso(data["now"]), data["timezone"], data.get("date_order", "DMY"))


@dataclass(frozen=True)
class Reminder:
    """A scheduled reminder. ``fired`` is derived at read time, never stored (AC-7.3)."""

    id: str
    title: str
    due_at: dt.datetime
    timezone: str
    status: str
    snooze_count: int
    created_at: dt.datetime
    updated_at: dt.datetime

    def to_dict(self) -> dict[str, Any]:
        local = self.due_at.astimezone(ZoneInfo(self.timezone))
        return {
            "id": self.id,
            "title": self.title,
            "due_at": local.isoformat(),
            "due_at_utc": fmt_utc(self.due_at),
            "timezone": self.timezone,
            "status": self.status,
            "snooze_count": self.snooze_count,
            "created_at": fmt_utc(self.created_at),
            "updated_at": fmt_utc(self.updated_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Reminder:
        zone = ZoneInfo(data["timezone"])
        return cls(
            id=data["id"],
            title=data["title"],
            due_at=parse_iso(data["due_at"]).astimezone(zone),
            timezone=data["timezone"],
            status=data["status"],
            snooze_count=int(data["snooze_count"]),
            created_at=parse_iso(data["created_at"]),
            updated_at=parse_iso(data["updated_at"]),
        )

    def with_changes(self, **changes: Any) -> Reminder:  # noqa: ANN401 - mirrors dataclasses.replace
        return replace(self, **changes)

    def effective_status(self, now: dt.datetime) -> str:
        if self.status == "scheduled" and self.due_at <= now:
            return "fired"
        return self.status
