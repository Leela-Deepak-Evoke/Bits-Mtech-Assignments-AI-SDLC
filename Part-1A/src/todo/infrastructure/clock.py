"""System clock adapter."""

from datetime import UTC, datetime

__all__ = ["SystemClock"]


class SystemClock:
    """Real UTC time truncated to whole seconds."""

    def now(self) -> datetime:
        """Return the current UTC time."""
        return datetime.now(UTC).replace(microsecond=0)
