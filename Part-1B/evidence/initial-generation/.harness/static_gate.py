"""Static gates with bounded deterministic self-healing (constitution Art. V + VII).

Gate order: compile -> format -> lint. Auto-fixable failures (ruff format / safe ruff fixes) are repaired
automatically, at most MAX_REPAIRS times; everything else is reported for a reasoned repair.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from common import ROOT

MAX_REPAIRS = 3
PATHS = ["src", "tests", ".harness", "evals"]


def _run(*args: str) -> tuple[int, str]:
    proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False)  # noqa: S603
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _gates() -> dict[str, tuple[int, str]]:
    py = sys.executable
    return {
        "compile": _run(py, "-m", "compileall", "-q", *PATHS),
        "format": _run(py, "-m", "ruff", "format", "--check", *PATHS),
        "lint": _run(py, "-m", "ruff", "check", "--no-fix", *PATHS),
    }


def run() -> dict[str, Any]:
    """Run the gates; heal what is deterministic. Returns a structured report for the evidence log."""
    cycles: list[dict[str, Any]] = []
    results = _gates()
    for attempt in range(1, MAX_REPAIRS + 1):
        failing = {g: out for g, (code, out) in results.items() if code != 0}
        fixable = [g for g in failing if g in {"format", "lint"}]
        if not fixable:
            break
        before = {g: failing[g][:600] for g in fixable}
        _run(sys.executable, "-m", "ruff", "check", "--fix", "--quiet", *PATHS)
        _run(sys.executable, "-m", "ruff", "format", *PATHS)
        results = _gates()
        remaining = [g for g, (code, _) in results.items() if code != 0]
        cycles.append({"attempt": attempt, "gates": fixable, "before": before, "after_failing": remaining})
    final = {g: {"ok": code == 0, "output": out[:4000]} for g, (code, out) in results.items()}
    return {"cycles": cycles, "final": final, "ok": all(v["ok"] for v in final.values())}


if __name__ == "__main__":
    report = run()
    print(report["ok"], [c["attempt"] for c in report["cycles"]])
