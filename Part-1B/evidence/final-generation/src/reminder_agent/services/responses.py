"""AgentResponse builders. All user-facing text is templated: no LLM text reaches a response (SAF-7)."""

from __future__ import annotations

from typing import Any

from reminder_agent.models import Reminder
from reminder_agent.sanitize import sanitize_text

SCHEMA_VERSION = "1.0"
QUESTION_PRIORITY = ["target", "title", "date", "time_meridiem", "date_order", "time", "duration"]
QUESTIONS = {
    "target": "Which reminder do you mean?",
    "title": "What should I remind you about?",
    "date": "What date should I set the reminder for?",
    "time_meridiem": "Is that AM or PM?",
    "date_order": "Is that day first or month first?",
    "time": "What time should I set it for?",
    "duration": "How long should I snooze it for, for example 15 minutes?",
}
REFUSALS = {
    "unsupported_intent": "I can only create a reminder, or reschedule or snooze one existing reminder.",
    "unsafe_request": "I can't help with that request.",
    "past_time": "That time is already in the past.",
    "out_of_range": "That time is too soon or too far ahead (limit: 2 years).",
    "reminder_not_found": "I couldn't find a matching reminder.",
    "invalid_state": "That reminder can no longer be changed.",
    "max_clarifications_exceeded": "I still can't tell what you want. Please start again with the task and a date.",
    "snooze_limit_reached": "This reminder has reached its snooze limit.",
    "input_invalid": "Please send a message of 1 to 1000 characters with a title of at most 200 characters.",
}
ERRORS = {
    "llm_unavailable": "The language service is unavailable. Please try again.",
    "llm_timeout": "The language service timed out. Please try again.",
    "llm_schema_violation": "I could not understand the language service reply. Please try again.",
    "storage_error": "I could not save the change. Nothing was changed.",
    "internal_error": "Something went wrong. Nothing was changed.",
}


def _base(kind: str, message: str) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "type": kind, "message": sanitize_text(message)[:500]}


def _when(reminder: Reminder) -> str:
    return reminder.due_at.strftime("%a %d %b %Y %H:%M")


def created(reminder: Reminder, assumptions: list[str]) -> dict[str, Any]:
    body = _base("reminder_created", f"Reminder set: {reminder.title} on {_when(reminder)}")
    return {**body, "reminder": reminder.to_dict(), "assumptions": assumptions}


def rescheduled(reminder: Reminder, previous: Reminder, assumptions: list[str]) -> dict[str, Any]:
    body = _base("reminder_rescheduled", f"Moved: {reminder.title} to {_when(reminder)}")
    return {
        **body,
        "reminder": reminder.to_dict(),
        "previous_due_at": previous.to_dict()["due_at"],
        "assumptions": assumptions,
    }


def snoozed(reminder: Reminder, previous: Reminder, minutes: int, assumptions: list[str]) -> dict[str, Any]:
    body = _base("reminder_snoozed", f"Snoozed: {reminder.title} until {_when(reminder)}")
    return {
        **body,
        "reminder": reminder.to_dict(),
        "previous_due_at": previous.to_dict()["due_at"],
        "snooze_minutes": minutes,
        "assumptions": assumptions,
    }


def clarification(
    intent: str, missing: list[str], partial: dict[str, str], round_: int, candidates: list[str] | None = None
) -> dict[str, Any]:
    ordered = [f for f in QUESTION_PRIORITY if f in missing]
    question = QUESTIONS[ordered[0]]
    body = _base("clarification_needed", question)
    body.update(intent=intent, missing_fields=ordered, question=question, round=round_, partial=partial)
    if candidates:
        body["candidates"] = candidates
    return body


def refused(reason: str) -> dict[str, Any]:
    return {**_base("refused", REFUSALS[reason]), "reason": reason}


def error(code: str) -> dict[str, Any]:
    return {**_base("error", ERRORS[code]), "code": code}
