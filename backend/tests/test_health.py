from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_graph_ok(app_env):
    with TestClient(app) as client:  # runs the lifespan: schema applied, graph opened
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "graph": "ok"}


def test_health_not_ready_without_lifespan(app_env):
    if hasattr(app.state, "graph"):
        del app.state.graph
    response = TestClient(app).get("/health")
    assert response.status_code == 503