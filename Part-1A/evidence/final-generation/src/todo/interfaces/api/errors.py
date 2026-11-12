"""Map errors to HTTP status codes and the uniform error body."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from todo.domain.errors import (
    InvalidTransitionError,
    StorageError,
    StorageFormatError,
    TaskNotFoundError,
    TodoError,
    ValidationError,
)
from todo.interfaces.api.security import UnauthorizedError

__all__ = ["register_error_handlers"]

_LOGGER = logging.getLogger(__name__)

_STATUS_CODES: tuple[tuple[type[TodoError], int], ...] = (
    (ValidationError, 422),
    (TaskNotFoundError, 404),
    (InvalidTransitionError, 409),
    (StorageError, 500),
    (StorageFormatError, 500),
)
_HTTP_CODES = {404: "not_found", 405: "method_not_allowed"}


def _body(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def register_error_handlers(app: FastAPI) -> None:
    """Install handlers so no internal detail ever leaks to clients."""

    @app.exception_handler(TodoError)
    async def _todo_error(_: Request, exc: TodoError) -> JSONResponse:
        for error_type, status in _STATUS_CODES:
            if isinstance(exc, error_type):
                if status == 500:  # noqa: PLR2004
                    _LOGGER.error("storage failure: %s", exc.message)
                    return _body(exc.code, "internal storage error", status)
                return _body(exc.code, exc.message, status)
        return _body("internal_error", "internal error", 500)

    @app.exception_handler(RequestValidationError)
    async def _request_invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'][1:]) or 'body'}: {error['msg']}"
            for error in exc.errors()
        )
        return _body("validation_error", details or "invalid request", 422)

    @app.exception_handler(UnauthorizedError)
    async def _unauthorized(_: Request, __: UnauthorizedError) -> JSONResponse:
        return _body("unauthorized", "missing or invalid API key", 401)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "http_error")
        return _body(code, str(exc.detail), exc.status_code)

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        _LOGGER.exception("unexpected error", exc_info=exc)
        return _body("internal_error", "internal error", 500)
