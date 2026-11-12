"""Ports for non-deterministic collaborators."""

from datetime import datetime
from typing import Protocol

__all__ = ["Clock"]


class Clock(Protocol):
    """Source of the current time."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC datetime."""
        ...
