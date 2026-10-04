from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.database import get_db
from app.services.payments import (
    DuplicateSquareRefundError,
    PaymentNotFoundError,
    PaymentNotRefundableError,
    RefundCurrencyMismatchError,
    RefundLimitExceededError,
    create_refund,
)


router = APIRouter(
    prefix="/api/refunds",
    tags=["refunds"],
)


@router.post(
    "",
    response_model=schemas.RefundRead,
    status_code=status.HTTP_201_CREATED,
)
def create_refund_endpoint(
    refund_data: schemas.RefundCreate,
    db: Session = Depends(get_db),
) -> models.Refund:
    """Record a refund against an existing completed payment."""

    try:
        return create_refund(db, refund_data)
    except PaymentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        DuplicateSquareRefundError,
        PaymentNotRefundableError,
        RefundLimitExceededError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except RefundCurrencyMismatchError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get(
    "",
    response_model=list[schemas.RefundRead],
)
def list_refunds(
    payment_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> list[models.Refund]:
    """List refunds with their payment summary, optionally filtered by payment."""

    statement = (
        select(models.Refund)
        .options(selectinload(models.Refund.payment))
        .order_by(models.Refund.created_at.desc())
    )
    if payment_id is not None:
        statement = statement.where(models.Refund.payment_id == payment_id)
    return list(db.scalars(statement).all())


@router.get(
    "/{refund_id}",
    response_model=schemas.RefundRead,
)
def get_refund(
    refund_id: int,
    db: Session = Depends(get_db),
) -> models.Refund:
    """Return a single refund with its associated payment summary."""

    refund = db.scalar(
        select(models.Refund)
        .options(selectinload(models.Refund.payment))
        .where(models.Refund.id == refund_id)
    )
    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    return refund
