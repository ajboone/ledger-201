from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db


router = APIRouter(
    prefix="/api/vendors",
    tags=["vendors"],
)


@router.post(
    "",
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


@router.get(
    "",
    response_model=list[schemas.VendorRead],
)
def list_vendors(
    db: Session = Depends(get_db),
) -> list[models.Vendor]:
    """Return all vendors in alphabetical order."""

    statement = select(models.Vendor).order_by(models.Vendor.name)

    vendors = db.scalars(statement).all()

    return list(vendors)