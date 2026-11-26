from fastapi import Request

from app.graph.client import GraphClient


def get_graph(request: Request) -> GraphClient:
    """The one shared GraphClient, created at startup (see main.py lifespan)."""
    return request.app.state.graph


def require_service_role() -> None:
    """PLACEHOLDER (Task 6): allows every caller.

    Task 15 replaces this with real authentication. Until then NEVER expose this API
    outside the Docker network (the backend port is not published).
    """
    return None