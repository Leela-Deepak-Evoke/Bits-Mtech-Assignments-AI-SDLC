"""Domain error hierarchy. Interfaces map these to exit codes / HTTP statuses."""

__all__ = [
    "InvalidTransitionError",
    "StorageError",
    "StorageFormatError",
    "TaskNotFoundError",
    "TodoError",
    "ValidationError",
]


class TodoError(Exception):
    """Base class for all expected application errors."""

    code = "todo_error"

    def __init__(self, message: str) -> None:
        """Store a human-readable message."""
        super().__init__(message)
        self.message = message


class ValidationError(TodoError):
    """Input violates a validation rule."""

    code = "validation_error"


class TaskNotFoundError(TodoError):
    """No task exists with the requested id."""

    code = "not_found"


class InvalidTransitionError(TodoError):
    """A status transition is not permitted."""

    code = "invalid_transition"


class StorageError(TodoError):
    """The data store could not be read or written."""

    code = "storage_error"


class StorageFormatError(TodoError):
    """The stored document is malformed (triggers corrupt-file recovery)."""

    code = "storage_error"
