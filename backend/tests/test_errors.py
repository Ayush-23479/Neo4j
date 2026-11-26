from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.errors import ApiError, install_error_handlers
from app.graph.client import GraphTimeout


class Body(BaseModel):
    amount: int = Field(gt=0)


def make_client() -> TestClient:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail /srv/app/db.py line 42")

    @app.get("/slow")
    def slow():
        raise GraphTimeout("query x exceeded 5 seconds")

    @app.get("/api-error")
    def api_error():
        raise ApiError(409, "conflict_thing", "Nope.")

    @app.post("/body")
    def body(b: Body):
        return b

    return TestClient(app, raise_server_exceptions=False)


def test_unknown_error_has_no_stack_trace():
    r = make_client().get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["error"] == "internal_error"
    assert "request_id" in body
    for leak in ("Traceback", "RuntimeError", "db.py", "secret internal"):
        assert leak not in r.text


def test_timeout_and_api_error_codes():
    client = make_client()
    assert client.get("/slow").json()["error"] == "graph_timeout"
    r = client.get("/api-error")
    assert r.status_code == 409 and r.json() == {"error": "conflict_thing", "message": "Nope."}


def test_validation_error_does_not_echo_values():
    r = make_client().post("/body", json={"amount": -999999})
    assert r.status_code == 422
    assert r.json()["error"] == "validation_error"
    assert "999999" not in r.text


def test_404_uses_error_shape():
    r = make_client().get("/missing")
    assert r.status_code == 404 and r.json()["error"] == "not_found"