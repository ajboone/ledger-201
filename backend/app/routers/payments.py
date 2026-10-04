from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.payments import (
    DuplicateSquarePaymentError,
    OrderNotFoundError,
    PaymentCurrencyMismatchError,
    create_payment,
)


router = APIRouter(
    prefix="/api/payments",
    tags=["payments"],
)


@router.post(
    "",
    response_model=schemas.PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_payment_endpoint(
    payment_data: schemas.PaymentCreate,
    db: Session = Depends(get_db),
) -> models.Payment:
    """Record a payment against an existing order."""

    try:
        return create_payment(db, payment_data)
    except OrderNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except DuplicateSquarePaymentError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except PaymentCurrencyMismatchError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get(
    "",
    response_model=list[schemas.PaymentRead],
)
def list_payments(
    order_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> list[models.Payment]:
    """List payments, optionally restricted to one order."""

    statement = select(models.Payment).order_by(models.Payment.created_at.desc())
    if order_id is not None:
        statement = statement.where(models.Payment.order_id == order_id)
    return list(db.scalars(statement).all())


@router.get(
    "/{payment_id}",
    response_model=schemas.PaymentRead,
)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
) -> models.Payment:
    """Return a single payment by its Ledger ID."""

    payment = db.get(models.Payment, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )
    return payment
