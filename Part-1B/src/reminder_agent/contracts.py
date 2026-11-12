"""Loads the JSON Schema contracts and validates payloads against them (INV-1)."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

_DIR = Path(__file__).parent / "contracts"


@cache
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def schema_errors(name: str, payload: Any) -> list[str]:  # noqa: ANN401 - arbitrary JSON
    """Return human-readable schema violations ([] when valid). ``name``: agent-response | extraction-result."""
    found = sorted(_validator(name).iter_errors(payload), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message[:160]}" for e in found]


def response_errors(payload: Any) -> list[str]:  # noqa: ANN401
    return schema_errors("agent-response", payload)


def extraction_errors(payload: Any) -> list[str]:  # noqa: ANN401
    return schema_errors("extraction-result", payload)
