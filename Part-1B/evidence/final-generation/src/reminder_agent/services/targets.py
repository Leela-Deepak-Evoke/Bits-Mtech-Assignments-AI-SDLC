"""Resolving which existing reminder a message refers to (FR-5.1 / FR-5.2)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from reminder_agent.models import Reminder
from reminder_agent.repositories.memory import MemoryStore

MAX_CANDIDATES = 5
_STOP = {"the", "my", "a", "an", "reminder", "reminders", "about", "to", "that", "one"}
_PRONOUNS = {"it", "that", "this", "that one", "the last one", "last one", "the last reminder"}
_ID = re.compile(r"^rem_[0-9a-z]{8,32}$")


@dataclass(frozen=True)
class Match:
    """kind: one | many | none (nothing matches) | missing (no usable reference)."""

    kind: str
    reminder: Reminder | None = None
    candidates: list[str] = field(default_factory=list)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP}


def find_target(reference: str | None, store: MemoryStore, last_touched: str | None) -> Match:
    if not reference or not reference.strip():
        return Match("missing")
    ref = " ".join(reference.lower().split())
    if _ID.match(ref):
        found = store.get(ref)
        return Match("one", found) if found else Match("none")
    if ref in _PRONOUNS:
        found = store.get(last_touched) if last_touched else None
        return Match("one", found) if found else Match("missing")
    items = store.list()
    exact = [r for r in items if r.title.lower() == ref]
    if len(exact) == 1:
        return Match("one", exact[0])
    wanted = _tokens(ref)
    matches = exact or ([r for r in items if wanted <= _tokens(r.title)] if wanted else [])
    if not matches:
        return Match("none")
    if len(matches) == 1:
        return Match("one", matches[0])
    recent = sorted(matches, key=lambda r: r.updated_at, reverse=True)[:MAX_CANDIDATES]
    return Match("many", candidates=[r.id for r in recent])
