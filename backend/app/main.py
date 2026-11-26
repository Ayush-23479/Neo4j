import os
from contextlib import asynccontextmanager
from pathlib import Path

import relate
from fastapi import FastAPI

from app.graph.schema import apply_schema


def relate_path() -> str:
    """Path of the single-file graph. Relate only treats a path ending in .rl as a file."""
    path = os.getenv("RELATE_PATH", "./data/graph.rl")
    if not path.endswith(".rl"):
        raise RuntimeError(
            f"RELATE_PATH must end with .rl (got {path!r}). Fix it in .env, e.g. ./data/graph.rl"
        )
    return path


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Task 3: create the schema once at startup. Task 5 moves this into GraphClient."""
    path = relate_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = relate.connect(path)  # opened, used and closed on this one thread
    try:
        apply_schema(conn)
    finally:
        conn.close()
    yield


app = FastAPI(
    title="Explainable Payment Holds",
    description="Synthetic data and PayPal sandbox only.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if os.getenv("DEMO_MODE") == "probe":  # Task 2 only: temporary probe routes
    from app.graph.probe_api import router as probe_router

    app.include_router(probe_router)