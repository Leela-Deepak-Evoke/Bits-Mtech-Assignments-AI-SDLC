"""Thin CLI over ``ReminderAgent.handle`` (FR-8). Contains no business logic."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

from reminder_agent.llm.anthropic_client import AnthropicExtractor
from reminder_agent.llm.base import Extractor
from reminder_agent.models import Ctx
from reminder_agent.repositories.memory import JsonFileStore
from reminder_agent.services.agent import ReminderAgent

EXIT_CODES = {"refused": 2, "error": 3}


def main(argv: list[str] | None = None, extractor: Extractor | None = None) -> int:
    parser = argparse.ArgumentParser(prog="remind", description="Natural-language reminders.")
    parser.add_argument("text", help="what to remind / reschedule / snooze, in plain English")
    parser.add_argument("--json", action="store_true", help="print the AgentResponse as JSON")
    parser.add_argument("--session", default="cli")
    parser.add_argument("--tz", default=os.environ.get("REMINDER_TZ", "Asia/Kolkata"))
    parser.add_argument("--date-order", choices=["DMY", "MDY", "unset"], default="DMY")
    parser.add_argument("--data-file", type=Path, default=Path(os.environ.get("REMINDER_DATA_FILE", "reminders.json")))
    args = parser.parse_args(argv)
    ctx = Ctx(dt.datetime.now(dt.timezone.utc), args.tz, args.date_order)  # noqa: UP017 - the one place real time enters
    agent = ReminderAgent(extractor or AnthropicExtractor(), JsonFileStore(args.data_file))
    response = agent.handle(args.session, args.text, ctx)
    print(json.dumps(response, ensure_ascii=False, indent=2) if args.json else response["message"])  # noqa: T201
    return EXIT_CODES.get(response["type"], 0)


if __name__ == "__main__":
    sys.exit(main())
