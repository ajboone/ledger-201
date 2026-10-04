from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.database import get_db
from app.services.orders import (
    DuplicateSquareOrderError,
    LocationNotFoundError,
    create_order as create_order_record,
)


router = APIRouter(
    prefix="/api/orders",
    tags=["orders"],
)


@router.post(
    "",
    response_model=schemas.OrderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order_data: schemas.OrderCreate,
    db: Session = Depends(get_db),
) -> models.Order:
    """Create a sales order with nested order line items."""

    try:
        return create_order_record(db, order_data)
    except LocationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except DuplicateSquareOrderError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.get(
    "",
    response_model=list[schemas.OrderRead],
)
def list_orders(
    db: Session = Depends(get_db),
) -> list[models.Order]:
    """Return all orders newest first."""

    statement = (
        select(models.Order)
        .options(selectinload(models.Order.line_items))
        .order_by(models.Order.created_at.desc())
    )
    orders = db.scalars(statement).all()
    return list(orders)


@router.get(
    "/{order_id}",
    response_model=schemas.OrderRead,
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
) -> models.Order:
    """Return a single order by ID."""

    order = db.scalar(
        select(models.Order)
        .options(selectinload(models.Order.line_items))
        .where(models.Order.id == order_id)
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    return order
