from fastapi import FastAPI

from app import models
from app.database import Base, engine


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Ledger 201",
    description="A restaurant expense and purchasing management system.",
    version="0.1.0",
)


@app.get("/")
def read_home() -> dict[str, str]:
    """Confirm that the Ledger 201 API is running."""

    return {"message": "Ledger 201 is running."}