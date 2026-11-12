"""Extraction port and an in-process replay adapter (used by tests and the evaluation harness)."""

from __future__ import annotations

import json
from typing import Protocol

from reminder_agent.errors import LlmTimeout
from reminder_agent.models import Ctx


class Extractor(Protocol):
    """LLM boundary. Returns the raw model text/dict for the extraction contract; never dates or ids."""

    def extract(self, message: str, ctx: Ctx, candidate_titles: list[str], feedback: str | None) -> str | dict: ...


class ReplayExtractor:
    """Serves pre-recorded extractions keyed by message, with optional fault injection.

    ``faults``: ``{"kind": "timeout"}`` or ``{"kind": "malformed_json", "times": n}``.
    """

    def __init__(self, recorded: dict[str, dict], faults: dict | None = None) -> None:
        self._recorded = recorded
        self._faults = faults or {}
        self.calls = 0
        self.returned: list[str | dict] = []

    def extract(self, message: str, ctx: Ctx, candidate_titles: list[str], feedback: str | None) -> str | dict:  # noqa: ARG002
        self.calls += 1
        kind = self._faults.get("kind")
        if kind == "timeout":
            raise LlmTimeout("replay timeout")
        if kind == "malformed_json" and self.calls <= int(self._faults.get("times", 1)):
            self.returned.append("not json {")
            return "not json {"
        payload = self._recorded.get(message)
        out: str | dict = json.dumps(payload) if payload is not None else "{}"
        self.returned.append(out)
        return out
