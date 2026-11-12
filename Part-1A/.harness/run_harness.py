"""Main harness runner: lint -> security -> tests, then an overall PASS/FAIL.

All stdout/stderr of every step is captured into ``.harness/harness-log.md`` (appended per run).

Usage:
    python .harness/run_harness.py                 # run all three checks
    python .harness/run_harness.py --fail-fast     # stop at the first failing check
    python .harness/run_harness.py --only lint     # lint | security | tests
    python .harness/run_harness.py --strict-trace  # fail if any spec AC lacks a test
    python .harness/run_harness.py --skip-audit    # offline: skip pip-audit (never use in CI)

Exit code: 0 = overall PASS, 1 = overall FAIL.
"""

import argparse
import platform
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import lint_check
import security_check
import test_runner
from _common import CheckResult, StepResult, report

LOG_FILE = Path(__file__).resolve().parent / "harness-log.md"
MAX_CAPTURE = 20_000


def _fence(text: str) -> str:
    text = text.strip()
    if len(text) > MAX_CAPTURE:
        text = text[:MAX_CAPTURE] + f"\n... [truncated, {len(text) - MAX_CAPTURE} more characters]"
    return f"```text\n{text or '(empty)'}\n```"


def _step_markdown(step: StepResult) -> str:
    verdict = "PASS" if step.passed else "FAIL"
    parts = [
        f"#### {verdict} — {step.name}",
        f"- command: `{step.command}`",
        f"- exit code: {step.returncode} · {step.seconds:.1f}s",
    ]
    if step.note:
        parts.append(f"- note: {step.note}")
    parts += ["", "stdout:", _fence(step.stdout), "", "stderr:", _fence(step.stderr), ""]
    return "\n".join(parts)


def render_log_entry(results: list[CheckResult], started: datetime) -> str:
    """Markdown for one harness run."""
    overall = all(result.passed for result in results)
    lines = [
        f"## Run {started.strftime('%Y-%m-%d %H:%M:%S')} UTC — {'PASS' if overall else 'FAIL'}",
        "",
        f"Python {platform.python_version()} on {platform.system()} {platform.release()}",
        "",
        "| Check | Result |",
        "|---|---|",
        *[f"| {r.name} | {'PASS' if r.passed else 'FAIL'} |" for r in results],
        "",
    ]
    for result in results:
        lines.append(f"### {result.name}")
        lines.append("")
        lines.extend(_step_markdown(step) for step in result.steps)
    lines += ["---", ""]
    return "\n".join(lines)


def append_log(entry: str, log_file: Path = LOG_FILE) -> None:
    """Append ``entry`` to the log, creating it with a header on first use."""
    if not log_file.exists():
        log_file.write_text(
            "# Harness log\n\nEach run appends one section: overall verdict, per-check results, "
            "and the captured stdout/stderr of every step.\n\n",
            encoding="utf-8",
        )
    with log_file.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(entry)


def build_parser() -> argparse.ArgumentParser:
    """Command-line options."""
    parser = argparse.ArgumentParser(description="Run lint, security and test checks.")
    parser.add_argument("--only", choices=["lint", "security", "tests"])
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--strict-trace", action="store_true")
    parser.add_argument("--skip-audit", action="store_true")
    parser.add_argument("--log", type=Path, default=LOG_FILE)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the selected checks sequentially and print/log the verdict."""
    args = build_parser().parse_args(argv)
    checks: dict[str, Callable[[], CheckResult]] = {
        "lint": lint_check.run,
        "security": lambda: security_check.run(skip_audit=args.skip_audit),
        "tests": lambda: test_runner.run(strict_trace=args.strict_trace),
    }
    selected = [args.only] if args.only else list(checks)
    started = datetime.now(UTC)
    results: list[CheckResult] = []
    for index, name in enumerate(selected, start=1):
        sys.stdout.write(f"\n=== [{index}/{len(selected)}] {name.upper()} ===\n")
        result = checks[name]()
        report(result)
        results.append(result)
        if args.fail_fast and not result.passed:
            sys.stdout.write("fail-fast: stopping after first failing check\n")
            break
    append_log(render_log_entry(results, started), args.log)
    overall = all(result.passed for result in results)
    summary = " | ".join(f"{r.name}: {'PASS' if r.passed else 'FAIL'}" for r in results)
    sys.stdout.write(f"\n{'=' * 60}\n{summary}\nHARNESS RESULT: {'PASS' if overall else 'FAIL'}\n")
    sys.stdout.write(f"log: {args.log}\n")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
