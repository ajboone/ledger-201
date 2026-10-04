from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.services.daily_review import (
    DailyReviewCurrencyError,
    LocationNotFoundError,
    get_daily_review,
)


router = APIRouter(
    prefix="/api/daily-review",
    tags=["daily-review"],
)


@router.get(
    "",
    response_model=schemas.DailyReview,
)
def read_daily_review(
    location_id: int = Query(..., gt=0),
    review_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
) -> schemas.DailyReview:
    """Return deterministic daily financial and item analysis."""

    try:
        return get_daily_review(db, location_id, review_date)
    except LocationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except DailyReviewCurrencyError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
