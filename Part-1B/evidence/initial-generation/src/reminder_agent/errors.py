"""Exception hierarchy. Interfaces map these to AgentResponse ``error`` codes in one place."""

from __future__ import annotations


class ReminderError(Exception):
    """Base class for all expected failures."""


class LlmTimeout(ReminderError):  # noqa: N818 - domain name reads better than *Error
    """The extraction call exceeded its time limit."""


class LlmUnavailable(ReminderError):  # noqa: N818
    """The extraction backend could not be reached or is not configured."""


class ExtractionInvalid(ReminderError):
    """The LLM output failed the extraction contract (after the allowed retry)."""


class StorageError(ReminderError):
    """The reminder store could not persist a change."""


class InvariantViolation(ReminderError):
    """A response failed a runtime invariant; it must never reach the caller."""
