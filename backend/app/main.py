from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.database import Base, engine
from app.routers import locations, vendors


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Ledger 201",
    description=(
        "An AI-assisted restaurant analysis and reconciliation platform."
    ),
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(vendors.router)
app.include_router(locations.router)


@app.get("/")
def read_home() -> dict[str, str]:
    """Confirm that the Ledger 201 API is running."""

    return {"message": "Ledger 201 is running."}