"""Typer CLI. Contains no business logic: parse, call the service, format."""

import functools
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, TypeVar

import typer

from todo.app.config import Settings
from todo.app.container import build_service
from todo.domain.errors import TodoError
from todo.interfaces.cli import render
from todo.interfaces.cli.errors import exit_code_for
from todo.services.task_service import TaskService, TaskView

__all__ = ["app", "run"]

app = typer.Typer(help="Smart Todo & Task manager.", no_args_is_help=True, add_completion=False)

F = TypeVar("F", bound=Callable[..., Any])
JsonOption = Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")]


def _handle_errors(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        try:
            return func(*args, **kwargs)
        except TodoError as error:
            typer.echo(f"error: {error.message}", err=True)
            raise typer.Exit(exit_code_for(error)) from error

    return wrapper  # type: ignore[return-value]


def _service(ctx: typer.Context) -> TaskService:
    settings: Settings = ctx.obj
    return build_service(
        settings, on_warning=lambda message: typer.echo(f"warning: {message}", err=True)
    )


def _show_one(view: TaskView, as_json: bool) -> None:
    typer.echo(render.to_json(view.as_dict()) if as_json else render.task_line(view))


@app.callback()
def main(
    ctx: typer.Context,
    data_file: Annotated[
        Path | None, typer.Option("--data-file", help="Path of the JSON data file.")
    ] = None,
) -> None:
    """Smart Todo & Task manager."""
    settings = Settings.from_env()
    if data_file is not None:
        settings = Settings(data_file, settings.api_key, settings.host, settings.port)
    ctx.obj = settings


@app.command()
@_handle_errors
def add(  # noqa: PLR0913, PLR0917
    ctx: typer.Context,
    title: Annotated[str, typer.Argument(help="Task title.")],
    desc: Annotated[str | None, typer.Option("--desc", help="Description.")] = None,
    priority: Annotated[str | None, typer.Option("--priority", help="low|medium|high.")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", help="Tag (repeatable).")] = None,
    due: Annotated[str | None, typer.Option("--due", help="Due date YYYY-MM-DD.")] = None,
    json_output: JsonOption = False,
) -> None:
    """Add a task."""
    data: dict[str, object] = {"title": title}
    if desc is not None:
        data["description"] = desc
    if priority is not None:
        data["priority"] = priority
    if tag:
        data["tags"] = tag
    if due is not None:
        data["due_date"] = due
    _show_one(_service(ctx).add_task(data), json_output)


@app.command("list")
@_handle_errors
def list_tasks(  # noqa: PLR0913, PLR0917
    ctx: typer.Context,
    status: Annotated[str | None, typer.Option("--status")] = None,
    priority: Annotated[str | None, typer.Option("--priority")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", help="Tag (repeatable).")] = None,
    match: Annotated[str, typer.Option("--match", help="all|any")] = "all",
    overdue: Annotated[bool | None, typer.Option("--overdue/--no-overdue")] = None,
    sort: Annotated[
        str, typer.Option("--sort", help="priority|due_date|created_at|id")
    ] = "priority",
    order: Annotated[str | None, typer.Option("--order", help="asc|desc")] = None,
    json_output: JsonOption = False,
) -> None:
    """List tasks with optional filters and sorting."""
    views = _service(ctx).list_tasks(
        status=status,
        priority=priority,
        tags=tag or (),
        match=match,
        overdue=overdue,
        sort=sort,
        order=order,
    )
    if json_output:
        typer.echo(render.to_json([view.as_dict() for view in views]))
    else:
        for view in views:
            typer.echo(render.task_line(view))


@app.command()
@_handle_errors
def show(
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(metavar="ID")],
    json_output: JsonOption = False,
) -> None:
    """Show one task."""
    view = _service(ctx).get_task(task_id)
    typer.echo(render.to_json(view.as_dict()) if json_output else render.task_detail(view))


@app.command()
@_handle_errors
def update(  # noqa: PLR0913, PLR0917
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(metavar="ID")],
    title: Annotated[str | None, typer.Option("--title")] = None,
    desc: Annotated[str | None, typer.Option("--desc")] = None,
    priority: Annotated[str | None, typer.Option("--priority")] = None,
    tag: Annotated[
        list[str] | None, typer.Option("--tag", help="Replace tags (repeatable).")
    ] = None,
    clear_tags: Annotated[bool, typer.Option("--clear-tags")] = False,
    due: Annotated[str | None, typer.Option("--due")] = None,
    clear_due: Annotated[bool, typer.Option("--clear-due")] = False,
    json_output: JsonOption = False,
) -> None:
    """Update fields of a task."""
    changes: dict[str, object] = {}
    if title is not None:
        changes["title"] = title
    if desc is not None:
        changes["description"] = desc
    if priority is not None:
        changes["priority"] = priority
    if tag:
        changes["tags"] = tag
    if clear_tags:
        changes["tags"] = []
    if due is not None:
        changes["due_date"] = due
    if clear_due:
        changes["due_date"] = None
    _show_one(_service(ctx).update_task(task_id, changes), json_output)


@app.command()
@_handle_errors
def delete(
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(metavar="ID")],
    yes: Annotated[bool, typer.Option("--yes", help="Confirm deletion.")] = False,
) -> None:
    """Delete a task (requires --yes)."""
    if not yes:
        typer.echo("error: refusing to delete without --yes", err=True)
        raise typer.Exit(2)
    _service(ctx).delete_task(task_id)
    typer.echo(f"deleted task {task_id}")


def _transition(ctx: typer.Context, task_id: int, status: str, json_output: bool) -> None:
    _show_one(_service(ctx).change_status(task_id, status), json_output)


@app.command()
@_handle_errors
def start(
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(metavar="ID")],
    json_output: JsonOption = False,
) -> None:
    """Mark a task in progress."""
    _transition(ctx, task_id, "in_progress", json_output)


@app.command()
@_handle_errors
def complete(
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(metavar="ID")],
    json_output: JsonOption = False,
) -> None:
    """Mark a task completed."""
    _transition(ctx, task_id, "completed", json_output)


@app.command()
@_handle_errors
def reopen(
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(metavar="ID")],
    json_output: JsonOption = False,
) -> None:
    """Reopen a completed task (back to pending)."""
    _transition(ctx, task_id, "pending", json_output)


@app.command("next")
@_handle_errors
def next_task(ctx: typer.Context, json_output: JsonOption = False) -> None:
    """Show the most actionable task."""
    view = _service(ctx).next_task()
    if json_output:
        typer.echo(render.to_json(view.as_dict() if view else None))
    elif view is None:
        typer.echo("No actionable task.")
    else:
        typer.echo(render.task_line(view))


def run() -> None:
    """Console-script entry point."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    app()
