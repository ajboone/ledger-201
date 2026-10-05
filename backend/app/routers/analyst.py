from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.services.analyst import (
    AnalystValidationError,
    compare_daily_performance,
    get_daily_summary,
    get_discount_summary,
    get_reconciliation_exceptions,
    get_refund_summary,
    get_top_items,
)
from app.services.daily_review import (
    DailyReviewCurrencyError,
    LocationNotFoundError,
)


router = APIRouter(
    prefix="/api/analyst",
    tags=["analyst"],
)


def _raise_analyst_http_error(error: Exception) -> None:
    if isinstance(error, LocationNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(error),
    ) from error


@router.get(
    "/daily-summary",
    response_model=schemas.AnalystDailySummary,
)
def read_daily_summary(
    location_id: int = Query(..., gt=0),
    review_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
) -> schemas.AnalystDailySummary:
    """Return compact financial facts for one location and local date."""

    try:
        return get_daily_summary(db, location_id, review_date)
    except (LocationNotFoundError, DailyReviewCurrencyError, AnalystValidationError) as error:
        _raise_analyst_http_error(error)


@router.get(
    "/reconciliation-exceptions",
    response_model=list[schemas.AnalystReconciliationException],
)
def read_reconciliation_exceptions(
    location_id: int = Query(..., gt=0),
    review_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
) -> list[schemas.AnalystReconciliationException]:
    """Return only orders that require reconciliation review."""

    try:
        return get_reconciliation_exceptions(db, location_id, review_date)
    except (LocationNotFoundError, DailyReviewCurrencyError, AnalystValidationError) as error:
        _raise_analyst_http_error(error)


@router.get(
    "/top-items",
    response_model=list[schemas.AnalystTopItem],
)
def read_top_items(
    location_id: int = Query(..., gt=0),
    review_date: date = Query(..., alias="date"),
    limit: int = Query(default=5, ge=1),
    db: Session = Depends(get_db),
) -> list[schemas.AnalystTopItem]:
    """Return ranked item performance for one location and local date."""

    try:
        return get_top_items(db, location_id, review_date, limit)
    except (LocationNotFoundError, DailyReviewCurrencyError, AnalystValidationError) as error:
        _raise_analyst_http_error(error)


@router.get(
    "/refunds",
    response_model=schemas.AnalystRefundSummary,
)
def read_refund_summary(
    location_id: int = Query(..., gt=0),
    review_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
) -> schemas.AnalystRefundSummary:
    """Return refund counts, completed totals, and transaction identifiers."""

    try:
        return get_refund_summary(db, location_id, review_date)
    except (LocationNotFoundError, DailyReviewCurrencyError, AnalystValidationError) as error:
        _raise_analyst_http_error(error)


@router.get(
    "/discounts",
    response_model=schemas.AnalystDiscountSummary,
)
def read_discount_summary(
    location_id: int = Query(..., gt=0),
    review_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
) -> schemas.AnalystDiscountSummary:
    """Return order discount totals and the affected order identifiers."""

    try:
        return get_discount_summary(db, location_id, review_date)
    except (LocationNotFoundError, DailyReviewCurrencyError, AnalystValidationError) as error:
        _raise_analyst_http_error(error)


@router.get(
    "/compare",
    response_model=schemas.AnalystDailyComparison,
)
def read_daily_comparison(
    location_id: int = Query(..., gt=0),
    date_a: date = Query(...),
    date_b: date = Query(...),
    db: Session = Depends(get_db),
) -> schemas.AnalystDailyComparison:
    """Compare two local business dates; all changes are date B minus date A."""

    try:
        return compare_daily_performance(db, location_id, date_a, date_b)
    except (LocationNotFoundError, DailyReviewCurrencyError, AnalystValidationError) as error:
        _raise_analyst_http_error(error)
