"""Request bodies. Shape only: the domain remains the source of truth for rules."""

from pydantic import BaseModel, ConfigDict

__all__ = ["StatusChange", "TaskCreate", "TaskUpdate"]


class TaskCreate(BaseModel):
    """Body of ``POST /tasks``."""

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str = ""
    priority: str = "medium"
    tags: list[str] = []
    due_date: str | None = None


class TaskUpdate(BaseModel):
    """Body of ``PATCH /tasks/{id}``; only supplied fields are applied."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    priority: str | None = None
    tags: list[str] | None = None
    due_date: str | None = None


class StatusChange(BaseModel):
    """Body of ``POST /tasks/{id}/status``."""

    model_config = ConfigDict(extra="forbid")

    status: str
