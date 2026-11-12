"""FastAPI application factory. No business logic: parse, call the service, format."""

from typing import Annotated, Any

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Query, Response

from todo.app.config import Settings
from todo.app.container import build_service
from todo.interfaces.api.errors import register_error_handlers
from todo.interfaces.api.schemas import StatusChange, TaskCreate, TaskUpdate
from todo.interfaces.api.security import build_api_key_guard
from todo.services.task_service import TaskService

__all__ = ["create_app", "create_app_from_env", "serve"]


def create_app(service: TaskService, api_key: str | None = None) -> FastAPI:
    """Build the API around ``service``."""
    app = FastAPI(title="Smart Todo API", version="1.0.0")
    register_error_handlers(app)
    router = APIRouter(dependencies=[Depends(build_api_key_guard(api_key))])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.post("/tasks", status_code=201, response_model=None)
    def create_task(payload: TaskCreate, response: Response) -> dict[str, Any]:
        view = service.add_task(payload.model_dump(exclude_unset=True))
        response.headers["Location"] = f"/tasks/{view.task.id}"
        return view.as_dict()

    @router.get("/tasks", response_model=None)
    def list_tasks(  # noqa: PLR0913, PLR0917
        status: str | None = None,
        priority: str | None = None,
        tag: Annotated[list[str] | None, Query()] = None,
        match: str = "all",
        overdue: bool | None = None,
        sort: str = "priority",
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        views = service.list_tasks(
            status=status,
            priority=priority,
            tags=tag or (),
            match=match,
            overdue=overdue,
            sort=sort,
            order=order,
        )
        return [view.as_dict() for view in views]

    @router.get("/tasks/next", response_model=None)
    def next_task() -> Any:  # noqa: ANN401
        view = service.next_task()
        if view is None:
            return Response(status_code=204)
        return view.as_dict()

    @router.get("/tasks/{task_id}", response_model=None)
    def get_task(task_id: int) -> dict[str, Any]:
        return service.get_task(task_id).as_dict()

    @router.patch("/tasks/{task_id}", response_model=None)
    def update_task(task_id: int, payload: TaskUpdate) -> dict[str, Any]:
        return service.update_task(task_id, payload.model_dump(exclude_unset=True)).as_dict()

    @router.delete("/tasks/{task_id}", status_code=204)
    def delete_task(task_id: int) -> Response:
        service.delete_task(task_id)
        return Response(status_code=204)

    @router.post("/tasks/{task_id}/status", response_model=None)
    def change_status(task_id: int, payload: StatusChange) -> dict[str, Any]:
        return service.change_status(task_id, payload.status).as_dict()

    app.include_router(router)
    return app


def create_app_from_env() -> FastAPI:
    """Factory for ``uvicorn --factory``: configuration comes from the environment."""
    settings = Settings.from_env()
    return create_app(build_service(settings), settings.api_key)


def serve() -> None:
    """Run the API, bound to ``TODO_HOST`` (default 127.0.0.1)."""
    settings = Settings.from_env()
    uvicorn.run(create_app_from_env(), host=settings.host, port=settings.port)
