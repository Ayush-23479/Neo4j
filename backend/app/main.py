from fastapi import FastAPI

app = FastAPI(
    title="Explainable Payment Holds",
    description="Synthetic data and PayPal sandbox only.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
