from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas


class OrderServiceError(Exception):
    """Base class for expected order-domain errors."""


class LocationNotFoundError(OrderServiceError):
    """Raised when an order references an unknown location."""


class DuplicateSquareOrderError(OrderServiceError):
    """Raised when a Square order ID is already assigned."""


def create_order(db: Session, order_data: schemas.OrderCreate) -> models.Order:
    """Persist an order and its line items as one transaction."""

    location = db.get(models.Location, order_data.location_id)
    if location is None:
        raise LocationNotFoundError("Location not found.")

    square_order_id = order_data.square_order_id or None
    if square_order_id is not None:
        existing_order = db.scalar(
            select(models.Order).where(
                models.Order.square_order_id == square_order_id
            )
        )
        if existing_order is not None:
            raise DuplicateSquareOrderError(
                "This Square order ID is already in use."
            )

    order = models.Order(
        provenance=order_data.provenance,
        square_order_id=square_order_id,
        location_id=location.id,
        state=order_data.state,
        currency=order_data.currency,
        created_at=order_data.created_at or datetime.now(timezone.utc),
        closed_at=order_data.closed_at,
        subtotal_amount=order_data.subtotal_amount,
        discount_amount=order_data.discount_amount,
        tax_amount=order_data.tax_amount,
        service_charge_amount=order_data.service_charge_amount,
        total_amount=order_data.total_amount,
        line_items=[
            models.OrderLineItem(
                square_line_item_id=line_item.square_line_item_id,
                catalog_object_id=line_item.catalog_object_id,
                item_name=line_item.item_name,
                variation_name=line_item.variation_name,
                category_name=line_item.category_name,
                quantity=line_item.quantity,
                unit_price_amount=line_item.unit_price_amount,
                gross_sales_amount=line_item.gross_sales_amount,
                discount_amount=line_item.discount_amount,
                total_amount=line_item.total_amount,
            )
            for line_item in order_data.line_items
        ],
    )

    try:
        db.add(order)
        db.flush()
        db.commit()
    except Exception:
        db.rollback()
        raise

    return order
