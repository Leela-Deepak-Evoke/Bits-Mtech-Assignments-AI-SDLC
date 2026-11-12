"""Parsing and validating the LLM's extraction output (INV-1, INV-3, SAF-5, SAF-8)."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

from reminder_agent.contracts import extraction_errors
from reminder_agent.errors import ExtractionInvalid

SPAN_FIELDS = ("title", "time", "duration", "target")


@dataclass(frozen=True)
class Extracted:
    """Span texts only (offsets are validated, then discarded). Mergeable across clarification turns."""

    intent: str
    title: str | None = None
    time: str | None = None
    duration: str | None = None
    target: str | None = None
    unsupported_reason: str | None = None

    def merged_with(self, newer: Extracted) -> Extracted | None:
        """Combine a pending request with a follow-up. None = conflict, so the follow-up is a new request."""
        if newer.intent == "unsupported":
            return None
        if newer.intent in {"reschedule", "snooze"} and self.intent not in {"unknown", newer.intent}:
            return None
        values: dict[str, str | None] = {}
        for name in SPAN_FIELDS:
            old, new = getattr(self, name), getattr(newer, name)
            if old and new:
                return None  # the follow-up restates something already known: treat it as a new request
            values[name] = old or new
        intent = newer.intent if self.intent == "unknown" else self.intent
        return replace(self, intent=intent, **values)


def _repair_span(message: str, span: dict) -> dict | None:
    """Fix wrong offsets only when the text occurs exactly once (plan risk: LLM off-by-one)."""
    text = span["text"]
    if message.count(text) != 1:
        return None
    start = message.index(text)
    return {"text": text, "start": start, "end": start + len(text)}


def parse_extraction(raw: str | dict, message: str) -> Extracted:
    """Return an ``Extracted`` or raise ``ExtractionInvalid`` describing the first problem."""
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError as exc:
        raise ExtractionInvalid("output is not valid JSON") from exc
    if not isinstance(data, dict):
        raise ExtractionInvalid("output is not a JSON object")
    problems = extraction_errors(data)
    if problems:
        raise ExtractionInvalid("; ".join(problems[:3]))
    texts: dict[str, str | None] = {}
    for name in SPAN_FIELDS:
        span = data[name]
        if span is not None and message[span["start"] : span["end"]] != span["text"]:
            span = _repair_span(message, span)
            if span is None:
                raise ExtractionInvalid(f"{name}: span does not match the message")
        texts[name] = span["text"] if span else None
    return Extracted(intent=data["intent"], unsupported_reason=data.get("unsupported_reason"), **texts)
