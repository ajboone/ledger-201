from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db


router = APIRouter(
    prefix="/api/locations",
    tags=["locations"],
)


@router.post(
    "",
    response_model=schemas.LocationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_location(
    location_data: schemas.LocationCreate,
    db: Session = Depends(get_db),
) -> models.Location:
    """Create and save a restaurant location."""

    normalized_name = location_data.name.strip()
    normalized_currency = location_data.currency.strip().upper()
    normalized_timezone = location_data.timezone.strip()

    existing_location = db.scalar(
        select(models.Location).where(
            func.lower(models.Location.name) == normalized_name.lower()
        )
    )

    if existing_location is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A location with this name already exists.",
        )

    if location_data.square_location_id is not None:
        normalized_square_id = location_data.square_location_id.strip()

        existing_square_location = db.scalar(
            select(models.Location).where(
                models.Location.square_location_id == normalized_square_id
            )
        )

        if existing_square_location is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This Square location ID is already in use.",
            )
    else:
        normalized_square_id = None

    location = models.Location(
        name=normalized_name,
        square_location_id=normalized_square_id,
        timezone=normalized_timezone,
        currency=normalized_currency,
    )

    db.add(location)
    db.commit()
    db.refresh(location)

    return location


@router.get(
    "",
    response_model=list[schemas.LocationRead],
)
def list_locations(
    db: Session = Depends(get_db),
) -> list[models.Location]:
    """Return all restaurant locations alphabetically."""

    statement = select(models.Location).order_by(models.Location.name)

    locations = db.scalars(statement).all()

    return list(locations)