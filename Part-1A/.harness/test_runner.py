"""Test runner: executes the spec-derived unit/integration/contract/architecture tests.

Steps:
  1. pytest over ``tests/`` with branch coverage (the coverage floor lives in pyproject.toml).
  2. Traceability report: every ``AC-x.y`` in ``.speckit/spec.md`` is matched against test names
     such as ``test_ac_5_2_...``. Informational by default; ``--strict-trace`` makes gaps fail.

Usage: ``python .harness/test_runner.py [--strict-trace]``  (exit 0 = PASS, 1 = FAIL)
"""

import re
import sys
from pathlib import Path

from _common import PYTHON, ROOT, CheckResult, StepResult, report, run_step

SPEC = ROOT / ".speckit" / "spec.md"
TESTS = ROOT / "tests"
_SPEC_AC = re.compile(r"^- \*\*AC-(\d+\.\d+)\*\*", re.MULTILINE)
_TEST_NAME = re.compile(r"def (test_ac_[a-z0-9_]+)\(")
_TEST_AC = re.compile(r"(?:ac|and)_(\d+)_(\d+)")


def spec_criteria(spec: Path = SPEC) -> list[str]:
    """Acceptance-criterion ids (``"5.2"``) declared in the specification."""
    return _SPEC_AC.findall(spec.read_text(encoding="utf-8"))


def referenced_criteria(tests: Path = TESTS) -> set[str]:
    """Acceptance-criterion ids referenced by test function names."""
    found: set[str] = set()
    for file in tests.rglob("test_*.py"):
        for name in _TEST_NAME.findall(file.read_text(encoding="utf-8")):
            found.update(f"{major}.{minor}" for major, minor in _TEST_AC.findall(name))
    return found


def traceability_step(*, strict: bool) -> StepResult:
    """Report which spec acceptance criteria have a referencing test."""
    declared = spec_criteria()
    tested = referenced_criteria()
    missing = [ac for ac in declared if ac not in tested]
    covered = len(declared) - len(missing)
    lines = [f"AC traceability: {covered}/{len(declared)} acceptance criteria referenced by tests"]
    if missing:
        lines.append("not yet referenced: " + ", ".join(f"AC-{ac}" for ac in missing))
    failed = strict and bool(missing)
    return StepResult(
        "AC traceability" + (" (strict)" if strict else " (informational)"),
        "match spec AC ids against test names",
        1 if failed else 0,
        "\n".join(lines),
    )


def run(*, strict_trace: bool = False) -> CheckResult:
    """Run pytest (with coverage) and the traceability report."""
    check = CheckResult("TESTS")
    check.steps = [
        run_step(
            "pytest (unit, integration, contract, architecture) + coverage",
            [
                PYTHON,
                "-m",
                "pytest",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
                "--cov",
                "--cov-report=term-missing:skip-covered",
            ],
        ),
        traceability_step(strict=strict_trace),
    ]
    return check


def main() -> int:
    """Console entry point."""
    result = run(strict_trace="--strict-trace" in sys.argv)
    report(result)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
