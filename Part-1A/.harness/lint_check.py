"""Lint / syntax guard (Constitution Art. V): compile, ruff check, ruff format, mypy --strict.

Usage: ``python .harness/lint_check.py``  (exit 0 = PASS, 1 = FAIL)
"""

import sys

from _common import PYTHON, CheckResult, report, run_step

TARGETS = ["src", "tests", ".harness"]


def run() -> CheckResult:
    """Run every lint step and return the combined result."""
    check = CheckResult("LINT")
    check.steps = [
        run_step("syntax (compileall)", [PYTHON, "-m", "compileall", "-q", *TARGETS]),
        run_step("ruff check", [PYTHON, "-m", "ruff", "check", *TARGETS]),
        run_step("ruff format --check", [PYTHON, "-m", "ruff", "format", "--check", *TARGETS]),
        run_step("mypy --strict", [PYTHON, "-m", "mypy"]),
    ]
    return check


def main() -> int:
    """Console entry point."""
    result = run()
    report(result)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
