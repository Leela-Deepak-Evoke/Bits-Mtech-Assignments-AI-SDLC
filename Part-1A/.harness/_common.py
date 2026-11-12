"""Shared helpers for the harness checks (not a package: scripts import it by sibling path)."""

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


@dataclass
class StepResult:
    """Outcome of one command or in-process check."""

    name: str
    command: str
    returncode: int
    stdout: str = ""
    stderr: str = ""
    seconds: float = 0.0
    note: str = ""

    @property
    def passed(self) -> bool:
        """A step passes only on exit code 0."""
        return self.returncode == 0


@dataclass
class CheckResult:
    """Outcome of a whole check (lint, security or tests)."""

    name: str
    steps: list[StepResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """A check passes only when every step passed."""
        return bool(self.steps) and all(step.passed for step in self.steps)


def run_step(name: str, command: list[str], *, timeout: int = 900) -> StepResult:
    """Run ``command`` from the project root, capturing stdout and stderr."""
    started = time.perf_counter()
    printable = " ".join(command).replace(PYTHON, "python")
    try:
        completed = subprocess.run(  # noqa: S603
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            env={**_utf8_env()},
        )
    except subprocess.TimeoutExpired as error:
        return StepResult(name, printable, 124, "", f"timed out after {error.timeout}s", timeout)
    except OSError as error:
        return StepResult(name, printable, 127, "", f"cannot execute: {error}")
    return StepResult(
        name,
        printable,
        completed.returncode,
        completed.stdout,
        completed.stderr,
        time.perf_counter() - started,
        _missing_tool_note(completed.stderr),
    )


def synthetic_step(name: str, description: str, problems: list[str]) -> StepResult:
    """Build a step for an in-process check: it fails when ``problems`` is non-empty."""
    body = "\n".join(problems) if problems else "no problems found"
    return StepResult(name, description, 1 if problems else 0, body)


def _utf8_env() -> dict[str, str]:
    return {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def _missing_tool_note(stderr: str) -> str:
    if "No module named" in stderr:
        return "tool not installed: run `pip install -e .[dev]`"
    return ""


def report(check: CheckResult) -> None:
    """Print a check's steps and verdict to the console."""
    for step in check.steps:
        verdict = "PASS" if step.passed else "FAIL"
        sys.stdout.write(f"  [{verdict}] {step.name} ({step.seconds:.1f}s)\n")
        if not step.passed:
            output = (step.stdout + step.stderr).strip()
            tail = "\n".join(output.splitlines()[-25:])
            sys.stdout.write(f"{_indent(tail)}\n")
            if step.note:
                sys.stdout.write(f"      note: {step.note}\n")
    sys.stdout.write(f"{check.name}: {'PASS' if check.passed else 'FAIL'}\n")


def _indent(text: str) -> str:
    return "\n".join(f"      {line}" for line in text.splitlines())
