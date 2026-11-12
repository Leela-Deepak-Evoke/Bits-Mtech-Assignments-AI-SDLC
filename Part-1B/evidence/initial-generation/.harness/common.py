"""Shared types and helpers for the three evaluation layers."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SPEC_CONTRACTS = ROOT / ".speckit" / "contracts"

# Independent of src/reminder_agent/sanitize.py on purpose: the harness must not reuse the code under test.
HIDDEN_CHARS = re.compile("[\u0000-\u0008\u000b-\u001f\u007f​-‍⁠﻿‪-‮⁦-⁩]")
LEAK_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (r"traceback", r"system prompt", r"anthropic_api_key", r"sk-ant", r"claude-", r"[A-Za-z]:\\\\?Users", r"/home/", r"\.py\b")
]


@dataclass(frozen=True)
class Finding:
    layer: int
    check: str
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"layer": self.layer, "check": self.check, "detail": self.detail}


def parse_iso(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


def dig(payload: dict[str, Any], dotted: str) -> Any:  # noqa: ANN401
    """Fetch ``a.b.c`` from nested dicts; returns a sentinel-free None when absent."""
    cur: Any = payload
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


SUCCESS_TYPES = {"reminder_created", "reminder_rescheduled", "reminder_snoozed"}
