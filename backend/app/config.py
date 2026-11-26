import os
from functools import lru_cache

from pydantic import BaseModel, Field


class Settings(BaseModel):
    relate_path: str = "./data/graph.rl"
    graph_query_dir: str | None = None
    graph_row_limit: int = Field(default=100, ge=1, le=10_000)
    graph_timeout_s: float = Field(default=5.0, gt=0, le=120)
    risk_threshold: int = 50
    mule_min_senders: int = 5
    mule_window_hours: int = 24
    demo_mode: str = "local"
    jwt_secret: str | None = None
    jwt_ttl_minutes: int = 15


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def load_settings() -> Settings:
    """Build Settings from the environment. Fails fast on an unsafe setup."""
    relate_path = _env("RELATE_PATH", "./data/graph.rl") or "./data/graph.rl"
    if not relate_path.endswith(".rl"):
        raise RuntimeError(
            f"RELATE_PATH must end with .rl (got {relate_path!r}). Fix it in .env, "
            "e.g. ./data/graph.rl"
        )
    settings = Settings(
        relate_path=relate_path,
        graph_query_dir=_env("GRAPH_QUERY_DIR"),
        graph_row_limit=int(_env("GRAPH_ROW_LIMIT", "100") or 100),
        graph_timeout_s=float(_env("GRAPH_TIMEOUT_S", "5") or 5),
        risk_threshold=int(_env("RISK_THRESHOLD", "50") or 50),
        mule_min_senders=int(_env("MULE_MIN_SENDERS", "5") or 5),
        mule_window_hours=int(_env("MULE_WINDOW_HOURS", "24") or 24),
        demo_mode=_env("DEMO_MODE", "local") or "local",
        jwt_secret=_env("JWT_SECRET"),
        jwt_ttl_minutes=int(_env("JWT_TTL_MINUTES", "15") or 15),
    )
    if settings.demo_mode != "local" and not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is required when DEMO_MODE is not 'local'.")
    return settings


@lru_cache
def get_settings() -> Settings:
    return load_settings()