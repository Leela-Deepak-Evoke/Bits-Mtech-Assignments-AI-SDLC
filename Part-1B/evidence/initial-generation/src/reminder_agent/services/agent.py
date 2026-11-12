"""The agent pipeline: Guard -> Extract -> Validate -> Policy -> invariant gate -> single commit (spec section 3)."""

from __future__ import annotations

import logging
import secrets
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from reminder_agent.errors import (
    ExtractionInvalid,
    InvariantViolation,
    LlmTimeout,
    LlmUnavailable,
    StorageError,
)
from reminder_agent.llm.base import Extractor
from reminder_agent.models import Ctx
from reminder_agent.repositories.memory import MemoryStore
from reminder_agent.services import intents, responses
from reminder_agent.services.extraction import Extracted, parse_extraction
from reminder_agent.services.invariants import response_problems

MAX_INPUT = 1000
MAX_ROUNDS = 3
MAX_EXTRACTION_ATTEMPTS = 2  # one call + one repair retry (SAF-8, SAF-9)
CANDIDATE_TITLES = 20
log = logging.getLogger("reminder_agent")


def default_ids() -> str:
    return "rem_" + secrets.token_hex(4)


@dataclass
class Session:
    pending: Extracted | None = None
    round: int = 0
    last_touched: str | None = None

    def reset(self) -> None:
        self.pending, self.round = None, 0


def guard(message: str) -> str | None:
    """NFC + trim; None when the message must be rejected before any LLM call (AC-1.4)."""
    try:
        message.encode("utf-8")
    except UnicodeEncodeError:
        return None
    cleaned = unicodedata.normalize("NFC", message).strip()
    return cleaned if 0 < len(cleaned) <= MAX_INPUT else None


class ReminderAgent:
    """Public entry point is :meth:`handle`. It never raises (AC-8.3)."""

    def __init__(self, extractor: Extractor, store: MemoryStore, new_id: Callable[[], str] = default_ids) -> None:
        self._extractor = extractor
        self._store = store
        self._new_id = new_id
        self._sessions: dict[str, Session] = {}

    def handle(self, session_id: str, message: str, ctx: Ctx) -> dict:
        session = self._sessions.setdefault(session_id, Session())
        try:
            return self._run(session, message, ctx)
        except LlmTimeout:
            return responses.error("llm_timeout")
        except LlmUnavailable:
            return responses.error("llm_unavailable")
        except ExtractionInvalid:
            return responses.error("llm_schema_violation")
        except StorageError:
            return responses.error("storage_error")
        except Exception as exc:  # noqa: BLE001 - last-resort net; type only is logged (SAF-7, SAF-10)
            log.error("internal_error type=%s", type(exc).__name__)
            return responses.error("internal_error")

    def _run(self, session: Session, message: str, ctx: Ctx) -> dict:
        cleaned = guard(message)
        if cleaned is None:
            return responses.refused("input_invalid")
        extracted = self._extract(cleaned, ctx)
        request = self._merge(session, extracted)
        result = self._decide(session, request, ctx)
        if result.response["type"] == "clarification_needed" and result.response["round"] > MAX_ROUNDS:
            session.reset()
            return responses.refused("max_clarifications_exceeded")
        if problems := response_problems(result.response, ctx):
            log.error("invariant_violation %s", problems[:3])
            raise InvariantViolation(problems[0])
        self._store.commit(add=result.add, update=result.update)  # the only write in the whole pipeline
        self._advance(session, result)
        return result.response

    def _extract(self, message: str, ctx: Ctx) -> Extracted:
        titles = [r.title for r in self._store.list()[:CANDIDATE_TITLES]]
        feedback: str | None = None
        for _ in range(MAX_EXTRACTION_ATTEMPTS):
            raw = self._extractor.extract(message, ctx, titles, feedback)
            try:
                return parse_extraction(raw, message)
            except ExtractionInvalid as exc:
                feedback = str(exc)
        raise ExtractionInvalid(feedback or "invalid extraction")

    @staticmethod
    def _merge(session: Session, extracted: Extracted) -> Extracted:
        if session.pending is not None:
            merged = session.pending.merged_with(extracted)
            if merged is not None:
                return merged
            session.reset()
        return extracted

    def _decide(self, session: Session, ex: Extracted, ctx: Ctx) -> intents.Result:
        round_ = session.round + 1
        intent = ex.intent
        if intent == "unknown" and (ex.title or ex.time):
            intent = "create"
        if intent == "unsupported":
            return intents.Result(responses.refused("unsupported_intent"))
        if intent == "create":
            return intents.create(ex, ctx, self._new_id(), round_)
        if intent == "reschedule":
            return intents.reschedule(ex, ctx, self._store, session.last_touched, round_)
        if intent == "snooze":
            return intents.snooze(ex, ctx, self._store, session.last_touched, round_)
        body = responses.clarification("unknown", ["title", "date"], {}, round_)
        return intents.Result(body, pending=ex)

    @staticmethod
    def _advance(session: Session, result: intents.Result) -> None:
        if result.pending is not None:
            session.pending, session.round = result.pending, result.response["round"]
            return
        session.reset()
        if result.touched:
            session.last_touched = result.touched
