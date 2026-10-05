from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas


class DailyReviewError(Exception):
    """Base class for daily review domain errors."""


class LocationNotFoundError(DailyReviewError):
    """Raised when the requested review location does not exist."""


class DailyReviewCurrencyError(DailyReviewError):
    """Raised when a daily review would combine incompatible currencies."""


def get_daily_review(
    db: Session,
    location_id: int,
    review_date: date,
    *,
    provenances: tuple[str, ...] | None = None,
) -> schemas.DailyReview:
    """Calculate daily order, payment, refund, and item totals deterministically.

    SQLite drops timezone offsets for the existing timezone-aware DateTime
    columns. Until timestamps are migrated to UTC, stored naive timestamps are
    interpreted as location-local wall times and filtered against local
    midnight boundaries. Associated payments and refunds are included with
    their order, regardless of their own creation date.
    """

    location = db.get(models.Location, location_id)
    if location is None:
        raise LocationNotFoundError("Location not found.")

    # SQLite drops timezone offsets from the existing timestamp columns, so
    # this MVP compares their stored location-local wall-clock values directly.
    start = datetime.combine(review_date, time.min)
    end = datetime.combine(review_date + timedelta(days=1), time.min)

    orders = list(
        db.scalars(
            select(models.Order)
            .where(
                models.Order.location_id == location.id,
                models.Order.created_at >= start,
                models.Order.created_at < end,
                models.Order.provenance.in_(provenances) if provenances is not None else True,
            )
            .order_by(models.Order.created_at, models.Order.id)
        ).all()
    )

    if any(order.currency != location.currency for order in orders):
        raise DailyReviewCurrencyError(
            "Daily review cannot combine orders in currencies different from the location currency."
        )

    order_ids = [order.id for order in orders]
    payments = (
        list(
            db.scalars(
                select(models.Payment).where(
                    models.Payment.order_id.in_(order_ids)
                )
            ).all()
        )
        if order_ids
        else []
    )
    payment_ids = [payment.id for payment in payments]
    refunds = (
        list(
            db.scalars(
                select(models.Refund).where(
                    models.Refund.payment_id.in_(payment_ids)
                )
            ).all()
        )
        if payment_ids
        else []
    )

    completed_payment_by_order: dict[int, int] = defaultdict(int)
    order_by_id = {order.id: order for order in orders}
    for payment in payments:
        if payment.currency != order_by_id[payment.order_id].currency:
            raise DailyReviewCurrencyError(
                "Daily review cannot combine payments in currencies different from their orders."
            )
        if payment.status == "COMPLETED":
            completed_payment_by_order[payment.order_id] += payment.amount

    payment_by_id = {payment.id: payment for payment in payments}
    completed_refund_by_order: dict[int, int] = defaultdict(int)
    for refund in refunds:
        payment = payment_by_id[refund.payment_id]
        if refund.currency != payment.currency:
            raise DailyReviewCurrencyError(
                "Daily review cannot combine refunds in currencies different from their payments."
            )
        if refund.status == "COMPLETED":
            completed_refund_by_order[payment.order_id] += refund.amount

    order_reconciliations: list[schemas.OrderReconciliation] = []
    for order in orders:
        completed_payment = completed_payment_by_order[order.id]
        completed_refund = completed_refund_by_order[order.id]
        net_collected = completed_payment - completed_refund
        difference = net_collected - order.total_amount
        order_reconciliations.append(
            schemas.OrderReconciliation(
                order_id=order.id,
                square_order_id=order.square_order_id,
                order_total_amount=order.total_amount,
                completed_payment_amount=completed_payment,
                completed_refund_amount=completed_refund,
                net_collected_amount=net_collected,
                difference=difference,
                status="RECONCILED" if difference == 0 else "REVIEW_REQUIRED",
            )
        )

    subtotal_amount = sum(order.subtotal_amount for order in orders)
    discount_amount = sum(order.discount_amount for order in orders)
    tax_amount = sum(order.tax_amount for order in orders)
    service_charge_amount = sum(order.service_charge_amount for order in orders)
    order_total_amount = sum(order.total_amount for order in orders)
    completed_payment_amount = sum(completed_payment_by_order.values())
    completed_refund_amount = sum(completed_refund_by_order.values())
    net_collected_amount = completed_payment_amount - completed_refund_amount
    reconciliation_difference = net_collected_amount - order_total_amount
    has_order_mismatch = any(
        reconciliation.status == "REVIEW_REQUIRED"
        for reconciliation in order_reconciliations
    )

    item_rows = (
        db.execute(
            select(
                models.OrderLineItem.item_name,
                models.OrderLineItem.quantity,
                models.OrderLineItem.gross_sales_amount,
                models.OrderLineItem.total_amount,
            )
            .join(models.Order, models.OrderLineItem.order_id == models.Order.id)
            .where(models.Order.id.in_(order_ids))
        ).all()
        if order_ids
        else []
    )
    item_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for item_name, quantity, gross_sales, total_sales in item_rows:
        totals = item_totals[item_name]
        totals[0] += quantity
        totals[1] += gross_sales
        totals[2] += total_sales
    top_items = [
        schemas.ItemSummary(
            item_name=item_name,
            quantity_sold=totals[0],
            gross_sales_amount=totals[1],
            total_sales_amount=totals[2],
        )
        for item_name, totals in sorted(
            item_totals.items(),
            key=lambda entry: (-entry[1][0], -entry[1][2], entry[0].casefold()),
        )
    ]

    return schemas.DailyReview(
        location_id=location.id,
        location_name=location.name,
        currency=location.currency,
        review_date=review_date,
        order_count=len(orders),
        subtotal_amount=subtotal_amount,
        discount_amount=discount_amount,
        tax_amount=tax_amount,
        service_charge_amount=service_charge_amount,
        order_total_amount=order_total_amount,
        completed_payment_amount=completed_payment_amount,
        completed_refund_amount=completed_refund_amount,
        net_collected_amount=net_collected_amount,
        average_order_value=(
            (order_total_amount + len(orders) // 2) // len(orders)
            if orders
            else 0
        ),
        reconciliation_difference=reconciliation_difference,
        reconciliation_status=(
            "REVIEW_REQUIRED"
            if reconciliation_difference != 0 or has_order_mismatch
            else "RECONCILED"
        ),
        orders=order_reconciliations,
        top_items=top_items,
    )
