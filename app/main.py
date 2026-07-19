from fastapi import FastAPI

app = FastAPI(
    title="Ledger 201",
    description="A restaurant expense and purchasing management system.",
    version="0.1.0",
)


@app.get("/")
def read_home() -> dict[str, str]:
    """Confirm that the Ledger 201 API is running."""
    return {"message": "Ledger 201 is running."}