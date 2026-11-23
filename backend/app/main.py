import os

from fastapi import FastAPI

app = FastAPI(
    title="Explainable Payment Holds",
    description="Synthetic data and PayPal sandbox only.",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    """Task 3: initialise the Relate graph schema and constraints once."""
    # Import here to avoid circular imports at module-load time
    from app.graph.schema import init_sql, apply_constraints, RELATE_PATH
    import relate

    path = os.getenv("RELATE_PATH", RELATE_PATH)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = relate.connect(path)
    # Run the idempotent schema initialisation strings
    for stmt in init_sql().split(" ; "):
        stmt = stmt.strip()
        if not stmt:
            continue
        try:
            conn.execute(stmt)
        except Exception:
            # IF NOT EXISTS / ADD INDEX IF NOT EXISTS may raise on very old versions;
            # we keep going so the app always starts.
            pass
    # Apply constraint guards (CREATE CONSTRAINT ... IF NOT EXISTS style)
    apply_constraints(conn)
    conn.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if os.getenv("DEMO_MODE") == "probe":  # Task 2 only: temporary probe routes
    from app.graph.probe_api import router as probe_router

    app.include_router(probe_router)