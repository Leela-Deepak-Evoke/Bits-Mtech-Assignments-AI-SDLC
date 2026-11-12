"""Shared fixtures: the specification's fixture clock (Thursday 2026-11-12 10:30 IST)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / ".harness"))
sys.path.insert(0, str(ROOT / "evals"))

from reminder_agent.models import Ctx  # noqa: E402


@pytest.fixture
def ctx() -> Ctx:
    return Ctx.from_dict({"now": "2026-11-12T10:30:00+05:30", "timezone": "Asia/Kolkata", "date_order": "DMY"})
