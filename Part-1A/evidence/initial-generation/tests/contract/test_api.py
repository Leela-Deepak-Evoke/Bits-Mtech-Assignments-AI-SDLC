from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import FakeClock
from todo.app.config import Settings
from todo.app.container import build_service
from todo.interfaces.api.app import create_app


@pytest.fixture
def client(tmp_path: Path, clock: FakeClock) -> TestClient:
    service = build_service(Settings(data_file=tmp_path / "api.json"), clock=clock)
    return TestClient(create_app(service), raise_server_exceptions=False)


def test_ac_11_1_crud_status_codes(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "Buy milk", "tags": ["Home"]})
    assert created.status_code == 201
    assert created.headers["location"] == "/tasks/1"
    assert created.json()["tags"] == ["home"]
    assert client.get("/tasks/1").status_code == 200
    patched = client.patch("/tasks/1", json={"priority": "high"})
    assert patched.status_code == 200
    assert patched.json()["priority"] == "high"
    moved = client.post("/tasks/1/status", json={"status": "in_progress"})
    assert moved.status_code == 200
    assert client.delete("/tasks/1").status_code == 204
    assert client.get("/tasks/1").status_code == 404
    assert client.get("/health").json() == {"status": "ok"}


def test_ac_11_5_repeated_tag_params_and_sorting(client: TestClient) -> None:
    client.post("/tasks", json={"title": "a", "tags": ["x", "y"], "priority": "low"})
    client.post("/tasks", json={"title": "b", "tags": ["x"], "priority": "high"})
    client.post("/tasks", json={"title": "c", "priority": "high"})
    both = client.get("/tasks", params=[("tag", "x"), ("tag", "y")]).json()
    assert [t["title"] for t in both] == ["a"]
    any_ = client.get("/tasks", params=[("tag", "y"), ("tag", "zzz"), ("match", "any")]).json()
    assert [t["title"] for t in any_] == ["a"]
    ordered = client.get("/tasks").json()
    assert [t["title"] for t in ordered] == ["b", "c", "a"]
    asc = client.get("/tasks", params={"sort": "priority", "order": "asc"}).json()
    assert [t["title"] for t in asc] == ["a", "b", "c"]


def test_ac_11_2_error_statuses_and_body_shape(client: TestClient) -> None:
    client.post("/tasks", json={"title": "a"})
    cases = [
        (client.get("/tasks/99"), 404, "not_found"),
        (client.post("/tasks", json={"title": " "}), 422, "validation_error"),
        (client.post("/tasks/1/status", json={"status": "completed"}), 200, None),
        (client.post("/tasks/1/status", json={"status": "in_progress"}), 409, "invalid_transition"),
        (client.post("/tasks/1/status", json={"status": "archived"}), 422, "validation_error"),
        (client.get("/tasks", params={"sort": "colour"}), 422, "validation_error"),
        (client.put("/tasks/1"), 405, "method_not_allowed"),
    ]
    for response, status, code in cases:
        assert response.status_code == status
        if code:
            assert set(response.json()) == {"error"}
            assert response.json()["error"]["code"] == code
            assert "Traceback" not in response.text


def test_ac_11_3_next_route_is_not_parsed_as_id(client: TestClient) -> None:
    assert client.get("/tasks/next").status_code == 204
    client.post("/tasks", json={"title": "a"})
    response = client.get("/tasks/next")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_ac_11_4_non_integer_id_is_422(client: TestClient) -> None:
    assert client.get("/tasks/abc").status_code == 422


def test_ac_11_6_malformed_json_is_422_not_500(client: TestClient) -> None:
    response = client.post("/tasks", content=b"{oops", headers={"content-type": "application/json"})
    assert response.status_code == 422


@pytest.mark.parametrize("field", ["id", "status", "created_at", "updated_at", "completed_at"])
def test_ac_1_10_system_fields_rejected_on_create(client: TestClient, field: str) -> None:
    assert client.post("/tasks", json={"title": "x", field: "1"}).status_code == 422


def test_ac_3_3_null_due_date_clears(client: TestClient) -> None:
    client.post("/tasks", json={"title": "a", "due_date": "2030-01-01"})
    assert client.patch("/tasks/1", json={"due_date": None}).json()["due_date"] is None
    assert client.patch("/tasks/1", json={}).status_code == 422


def test_ac_11_7_api_key_required_when_configured(tmp_path: Path, clock: FakeClock) -> None:
    service = build_service(Settings(data_file=tmp_path / "k.json"), clock=clock)
    secured = TestClient(create_app(service, api_key="s3cret"))
    assert secured.get("/health").status_code == 200
    denied = secured.post("/tasks", json={"title": "x"})
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "unauthorized"
    assert secured.post("/tasks", json={"title": "x"}, headers={"X-API-Key": "bad"}).status_code == 401
    assert secured.get("/tasks", headers={"X-API-Key": "s3cret"}).json() == []
    assert secured.post("/tasks", json={"title": "x"}, headers={"X-API-Key": "s3cret"}).status_code == 201


def test_ac_11_8_default_host_is_localhost() -> None:
    assert Settings.from_env({}).host == "127.0.0.1"


def test_storage_errors_do_not_leak_internals(tmp_path: Path, clock: FakeClock) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    service = build_service(Settings(data_file=blocker / "sub" / "d.json"), clock=clock)
    client = TestClient(create_app(service), raise_server_exceptions=False)
    response = client.post("/tasks", json={"title": "x"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "storage_error"
    assert "blocker" not in response.text
