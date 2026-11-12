"""Every dataset case, through the real agent and all three harness layers, must have zero findings."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATASET = json.loads((ROOT / "evals" / "dataset.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", DATASET["cases"], ids=lambda c: c["id"])
def test_case_has_no_findings(case: dict) -> None:
    import run_eval  # noqa: PLC0415 - path set up in conftest

    summary, _ = run_eval.evaluate_case(case, DATASET)
    assert summary["findings"] == []
