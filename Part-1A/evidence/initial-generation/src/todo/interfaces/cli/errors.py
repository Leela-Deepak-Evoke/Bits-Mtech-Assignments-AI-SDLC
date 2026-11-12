"""Map domain errors to process exit codes."""

from todo.domain.errors import (
    InvalidTransitionError,
    StorageError,
    StorageFormatError,
    TaskNotFoundError,
    TodoError,
    ValidationError,
)

__all__ = ["exit_code_for"]

_EXIT_CODES: tuple[tuple[type[TodoError], int], ...] = (
    (ValidationError, 2),
    (TaskNotFoundError, 3),
    (InvalidTransitionError, 4),
    (StorageError, 5),
    (StorageFormatError, 5),
)


def exit_code_for(error: TodoError) -> int:
    """Return the CLI exit code for ``error``."""
    for error_type, code in _EXIT_CODES:
        if isinstance(error, error_type):
            return code
    return 1
