from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import Base, engine, get_db


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

@app.get("/")
def read_home() -> dict[str, str]:
    """Confirm that the Ledger 201 API is running."""

    return {"message": "Ledger 201 is running."}


@app.post(
    "/api/vendors",
    response_model=schemas.VendorRead,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor(
    vendor_data: schemas.VendorCreate,
    db: Session = Depends(get_db),
) -> models.Vendor:
    """Create and save a restaurant vendor."""

    normalized_name = vendor_data.name.strip()

    existing_vendor = db.scalar(
        select(models.Vendor).where(
            func.lower(models.Vendor.name) == normalized_name.lower()
        )
    )

    if existing_vendor is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A vendor with this name already exists.",
        )

    vendor = models.Vendor(name=normalized_name)

    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    return vendor


@app.get(
    "/api/vendors",
    response_model=list[schemas.VendorRead],
)
def list_vendors(
    db: Session = Depends(get_db),
) -> list[models.Vendor]:
    """Return all vendors in alphabetical order."""

    statement = select(models.Vendor).order_by(models.Vendor.name)

    vendors = db.scalars(statement).all()

    return list(vendors)