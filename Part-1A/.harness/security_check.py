"""Security guard (Constitution Art. VI).

Steps:
  1. bandit static analysis of ``src`` (medium+ severity fails).
  2. Forbidden-construct scan (AST): eval/exec, pickle/marshal, shell=True, os.system, yaml.load.
  3. detect-secrets scan for committed credentials.
  4. pip-audit of the project's declared dependencies (known vulnerabilities).

Usage: ``python .harness/security_check.py [--skip-audit]``  (exit 0 = PASS, 1 = FAIL)
``--skip-audit`` exists only for offline work; the main harness never passes it.
"""

import ast
import json
import sys
from pathlib import Path

from _common import PYTHON, ROOT, CheckResult, StepResult, report, run_step, synthetic_step

SECRET_SCAN_PATHS = ["src", "tests", "pyproject.toml", ".harness"]
BANNED_IMPORTS = {"pickle", "marshal", "shelve"}
BANNED_CALLS = {"eval", "exec"}


def find_forbidden_constructs(root: Path) -> list[str]:
    """Return ``file:line: message`` for every dangerous construct under ``root/src``."""
    problems: list[str] = []
    for file in sorted((root / "src").rglob("*.py")):
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        relative = file.relative_to(root)
        for node in ast.walk(tree):
            message = _inspect(node)
            if message:
                problems.append(f"{relative}:{getattr(node, 'lineno', 0)}: {message}")
    return problems


def _inspect(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        banned = BANNED_IMPORTS & {alias.name.split(".")[0] for alias in node.names}
        return f"import of {sorted(banned)[0]} is forbidden" if banned else None
    if isinstance(node, ast.ImportFrom) and node.module:
        top = node.module.split(".")[0]
        return f"import of {top} is forbidden" if top in BANNED_IMPORTS else None
    if isinstance(node, ast.Call):
        return _inspect_call(node)
    return None


def _inspect_call(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name) and func.id in BANNED_CALLS:
        return f"call to {func.id}() is forbidden"
    if isinstance(func, ast.Attribute):
        dotted = f"{getattr(func.value, 'id', '')}.{func.attr}"
        if dotted in {"os.system", "yaml.load"}:
            return f"call to {dotted}() is forbidden"
    for keyword in node.keywords:
        if keyword.arg == "shell" and getattr(keyword.value, "value", False) is True:
            return "shell=True is forbidden"
    return None


def secrets_step() -> StepResult:
    """Run detect-secrets and fail if it reports any finding."""
    step = run_step(
        "detect-secrets",
        [PYTHON, "-m", "detect_secrets", "scan", "--all-files", *SECRET_SCAN_PATHS],
    )
    if not step.passed:
        return step
    try:
        findings = json.loads(step.stdout).get("results", {})
    except json.JSONDecodeError:
        step.returncode = 1
        step.stderr += "\ncould not parse detect-secrets output"
        return step
    if findings:
        step.returncode = 1
        step.stderr += "\npossible secrets: " + ", ".join(sorted(findings))
    return step


def run(*, skip_audit: bool = False) -> CheckResult:
    """Run every security step and return the combined result."""
    check = CheckResult("SECURITY")
    check.steps = [
        run_step("bandit (medium+)", [PYTHON, "-m", "bandit", "-r", "src", "-ll", "-q"]),
        synthetic_step(
            "forbidden constructs (AST)",
            "scan src for eval/exec/pickle/shell=True/os.system/yaml.load",
            find_forbidden_constructs(ROOT),
        ),
        secrets_step(),
    ]
    if not skip_audit:
        check.steps.append(
            run_step(
                "pip-audit (dependencies)",
                [PYTHON, "-m", "pip_audit", "--progress-spinner", "off", str(ROOT)],
            )
        )
    return check


def main() -> int:
    """Console entry point."""
    result = run(skip_audit="--skip-audit" in sys.argv)
    report(result)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
