"""LAYER 1 - structural schema validation.

Validates every response and every extraction against the AUTHORITATIVE schemas in .speckit/contracts
(not the packaged copy), and checks the packaged copy has not drifted from them.
"""

from __future__ import annotations

import json
from functools import cache
from typing import Any

from common import ROOT, SPEC_CONTRACTS, Finding
from jsonschema import Draft202012Validator

LAYER = 1


@cache
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SPEC_CONTRACTS / f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def contract_sync() -> list[Finding]:
    """The packaged schemas must be byte-identical to the specification's (plan T005)."""
    found = []
    for name in ("agent-response", "extraction-result"):
        spec = (SPEC_CONTRACTS / f"{name}.schema.json").read_bytes()
        packaged = (ROOT / "src" / "reminder_agent" / "contracts" / f"{name}.schema.json").read_bytes()
        if spec != packaged:
            found.append(Finding(LAYER, "L1.contract-sync", f"{name} schema differs between .speckit and package"))
    return found


def check_response(response: Any) -> list[Finding]:  # noqa: ANN401
    errors = sorted(_validator("agent-response").iter_errors(response), key=lambda e: list(e.absolute_path))
    out = [
        Finding(LAYER, "L1.response-schema", f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message[:140]}")
        for e in errors
    ]
    try:
        json.dumps(response)
    except (TypeError, ValueError) as exc:
        out.append(Finding(LAYER, "L1.json-serialisable", str(exc)[:140]))
    return out


def check_extraction(extraction: Any) -> list[Finding]:  # noqa: ANN401
    errors = _validator("extraction-result").iter_errors(extraction)
    return [Finding(LAYER, "L1.extraction-schema", e.message[:140]) for e in errors]
