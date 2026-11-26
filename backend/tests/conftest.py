import pytest

from app.config import get_settings


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    """Point the app at its own temporary graph file."""
    monkeypatch.setenv("RELATE_PATH", str(tmp_path / "app_test.rl"))
    monkeypatch.setenv("DEMO_MODE", "local")
    monkeypatch.delenv("GRAPH_QUERY_DIR", raising=False)
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()