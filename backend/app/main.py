import os

from fastapi import FastAPI

app = FastAPI(
    title="Explainable Payment Holds",
    description="Synthetic data and PayPal sandbox only.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if os.getenv("DEMO_MODE") == "probe":  # Task 2 only: temporary probe routes
    from app.graph.probe_api import router as probe_router

    app.include_router(probe_router)
