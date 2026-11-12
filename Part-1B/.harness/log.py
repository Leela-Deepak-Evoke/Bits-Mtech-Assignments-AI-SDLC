"""Append-only evidence log (evidence/harness-log.md) and its small CLI.

    python .harness/log.py repair --cycle N --gate G --failure F --root-cause R --action A [--files a,b]
    python .harness/log.py decision --decision ACCEPT|REJECT --by "<reviewer name>" --notes "..."

Only a human reviewer may run the `decision` command: it records the final ACCEPT / REJECT.
"""

from __future__ import annotations

import argparse
import datetime as dt

from common import ROOT

LOG = ROOT / "evidence" / "harness-log.md"
HEADER = """# Harness Log - Natural-Language Reminder Agent (Part-1B)

Append-only. Every harness run, every repair cycle, and the final human decision are recorded here.
Repair cycles follow constitution Art. VII: max 3 attempts per gate, no weakening of tests / datasets / thresholds.

"""


def stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")  # noqa: UP017


def append(text: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if not LOG.exists():
        LOG.write_text(HEADER, encoding="utf-8")
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n\n")


def log_repair(cycle: int, gate: str, failure: str, root_cause: str, action: str, files: str = "") -> None:
    append(
        f"## {stamp()} - REPAIR cycle {cycle} ({gate})\n\n"
        f"- **Failure:** {failure}\n- **Root cause:** {root_cause}\n- **Action:** {action}\n"
        f"- **Files changed:** {files or 'n/a'}\n- **Gate weakened / test or dataset edited:** NO"
    )


def log_decision(decision: str, by: str, notes: str) -> None:
    append(f"## {stamp()} - FINAL HUMAN DECISION: **{decision}**\n\n- **Reviewer:** {by}\n- **Notes:** {notes}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("repair")
    for name in ("gate", "failure", "root-cause", "action"):
        rep.add_argument(f"--{name}", required=True)
    rep.add_argument("--cycle", type=int, required=True)
    rep.add_argument("--files", default="")
    dec = sub.add_parser("decision")
    dec.add_argument("--decision", choices=["ACCEPT", "REJECT"], required=True)
    dec.add_argument("--by", required=True)
    dec.add_argument("--notes", default="")
    args = parser.parse_args()
    if args.command == "repair":
        log_repair(args.cycle, args.gate, args.failure, args.root_cause, args.action, args.files)
    else:
        log_decision(args.decision, args.by, args.notes)


if __name__ == "__main__":
    main()
