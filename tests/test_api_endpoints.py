from fastapi.testclient import TestClient

from smart_warehouse.server.app import app
from smart_warehouse.server.dependencies import (
    get_simulation_service,
    reset_repository,
    reset_simulation_service,
)


client = TestClient(app)


def setup_function() -> None:
    reset_simulation_service()
    reset_repository()


def test_health_endpoints() -> None:
    live = client.get("/api/v1/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"

    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_simulation_state_endpoint() -> None:
    response = client.get("/api/v1/simulation/state")
    assert response.status_code == 200
    payload = response.json()
    assert "packages" in payload
    assert "layout" in payload
    assert payload["layout"]["width"] > 0


def test_spawn_package_endpoint() -> None:
    service = get_simulation_service()
    service.simulator.packages.clear()

    response = client.post("/api/v1/simulation/packages")
    assert response.status_code == 201
    package = response.json()
    assert package["id"]
    assert package["status"] == "queued"

    state = client.get("/api/v1/simulation/state").json()
    assert len(state["packages"]) >= 1


def test_complete_package_and_events() -> None:
    service = get_simulation_service()
    service.simulator.packages.clear()

    created = client.post("/api/v1/simulation/packages").json()
    package_id = created["id"]

    completed = client.post(f"/api/v1/simulation/packages/{package_id}/complete")
    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == "delivered"

    events = client.get("/api/v1/simulation/events")
    assert events.status_code == 200
    payload = events.json()
    assert any(event["type"] == "package_completed" for event in payload)


def test_reset_endpoint() -> None:
    client.post("/api/v1/simulation/packages")
    reset = client.post("/api/v1/simulation/reset")
    assert reset.status_code == 204
    state = client.get("/api/v1/simulation/state").json()
    assert len(state["packages"]) == 0


def test_configuration_endpoint() -> None:
    response = client.get("/api/v1/simulation/config")
    assert response.status_code == 200
    config = response.json()
    assert "environment" in config
    assert "mqtt" in config


def test_observability_metrics() -> None:
    response = client.get("/api/v1/observability/metrics")
    assert response.status_code == 200
    assert "smart_warehouse_api_requests_total" in response.text


def test_robot_health_endpoints() -> None:
    health = client.get("/api/v1/robots/health")
    assert health.status_code == 200
    assert isinstance(health.json(), list)

    recover = client.post("/api/v1/robots/AGV-1/recover")
    assert recover.status_code == 404
