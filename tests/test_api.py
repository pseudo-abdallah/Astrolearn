"""Exercise the real API and SQLite store using isolated temporary files."""

import pytest
from fastapi.testclient import TestClient

from astrolearn.main import create_app


@pytest.fixture
def client(tmp_path):
    # Context manager runs startup, including database initialization.
    with TestClient(create_app(tmp_path / "test.sqlite3")) as instance:
        yield instance


def test_health_and_disconnected_capabilities(client):
    assert "AstroLearn" in client.get("/").text
    assert client.get("/api/v1/info").json()["name"] == "AstroLearn"
    assert client.get("/api/v1/health").json()["status"] == "ok"
    status = client.get("/api/v1/status").json()
    assert status["hardware"] == {"connected": False, "mode": "disconnected"}
    assert status["capabilities"]["motor_control"] is False
    assert status["capabilities"]["camera_capture"] is False


def test_catalog_and_missing_items(client):
    items = client.get("/api/v1/objects").json()
    assert len(items) == 3
    assert client.get("/api/v1/objects/moon").json()["name"] == "Moon"
    assert client.get("/api/v1/objects/unknown").status_code == 404
    assert client.get("/api/v1/observations/99").status_code == 404


def test_observation_round_trip_and_pagination(client):
    assert client.get("/api/v1/observations").json() == []
    payload = {"target": "  Moon  ", "notes": "User-entered demonstration note"}
    response = client.post("/api/v1/observations", json=payload)
    assert response.status_code == 201
    first = response.json()
    assert first["target"] == "Moon"
    assert first["created_at"].endswith("Z")
    assert client.get(f'/api/v1/observations/{first["id"]}').json() == first
    second = client.post("/api/v1/observations", json={"target": "Saturn"}).json()
    assert client.get("/api/v1/observations?limit=1").json() == [second]
    assert client.get("/api/v1/observations?limit=1&offset=1").json() == [first]


@pytest.mark.parametrize("payload", [
    {}, {"target": " "}, {"target": "a" * 121},
    {"target": "Moon", "notes": "a" * 4001},
    {"target": "Moon", "motor_speed": 100}, {"target": 123},
])
def test_invalid_observations(client, payload):
    assert client.post("/api/v1/observations", json=payload).status_code == 422
    assert client.get("/api/v1/observations").json() == []


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "limit=abc"])
def test_invalid_pagination(client, query):
    assert client.get(f"/api/v1/observations?{query}").status_code == 422


def test_persistence_and_sql_parameterization(tmp_path):
    path = tmp_path / "nested" / "observations.sqlite3"
    target = "Moon'); DROP TABLE observations; --"
    with TestClient(create_app(path)) as first:
        saved = first.post("/api/v1/observations", json={"target": target}).json()
    with TestClient(create_app(path)) as restarted:
        assert restarted.get("/api/v1/observations").json() == [saved]
    with TestClient(create_app(tmp_path / "other.sqlite3")) as isolated:
        assert isolated.get("/api/v1/observations").json() == []


def test_openapi_documents_contract(client):
    schema = client.get("/openapi.json").json()
    assert "201" in schema["paths"]["/api/v1/observations"]["post"]["responses"]
    assert client.get("/docs").status_code == 200
