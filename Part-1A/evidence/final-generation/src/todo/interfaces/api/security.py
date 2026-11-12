"""Optional shared API-key authentication."""

import secrets
from collections.abc import Callable
from typing import Annotated

from fastapi import Header

__all__ = ["UnauthorizedError", "build_api_key_guard"]


class UnauthorizedError(Exception):
    """Missing or wrong API key."""


def build_api_key_guard(expected: str | None) -> Callable[..., None]:
    """Return a dependency enforcing ``X-API-Key`` when ``expected`` is set."""

    def guard(x_api_key: Annotated[str | None, Header()] = None) -> None:
        if expected is None:
            return
        if x_api_key is None or not secrets.compare_digest(
            x_api_key.encode("utf-8"), expected.encode("utf-8")
        ):
            raise UnauthorizedError

    return guard
