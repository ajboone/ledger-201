from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.services.daily_review import LocationNotFoundError, get_daily_review


class AnalystValidationError(ValueError):
    """Raised when an analyst query contains invalid arguments."""


def validate_location(db: Session, location_id: int) -> None:
    """Raise the shared domain error when an analyst location does not exist."""

    if db.get(models.Location, location_id) is None:
        raise LocationNotFoundError("Location not found.")


def _validate_date(value: date, name: str) -> None:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise AnalystValidationError(f"{name} must be a calendar date.")


def _get_review(
    db: Session,
    location_id: int,
    review_date: date,
) -> schemas.DailyReview:
    _validate_date(review_date, "review_date")
    return get_daily_review(db, location_id, review_date)


def get_daily_summary(
    db: Session,
    location_id: int,
    review_date: date,
) -> schemas.AnalystDailySummary:
    """Return the financial totals calculated by the canonical Daily Review."""

    review = _get_review(db, location_id, review_date)
    return schemas.AnalystDailySummary(
        location_id=review.location_id,
        currency=review.currency,
        review_date=review.review_date,
        order_count=review.order_count,
        subtotal_amount=review.subtotal_amount,
        discount_amount=review.discount_amount,
        tax_amount=review.tax_amount,
        service_charge_amount=review.service_charge_amount,
        order_total_amount=review.order_total_amount,
        completed_payment_amount=review.completed_payment_amount,
        completed_refund_amount=review.completed_refund_amount,
        net_collected_amount=review.net_collected_amount,
        average_order_value=review.average_order_value,
        reconciliation_difference=review.reconciliation_difference,
        reconciliation_status=review.reconciliation_status,
    )


def get_reconciliation_exceptions(
    db: Session,
    location_id: int,
    review_date: date,
) -> list[schemas.AnalystReconciliationException]:
    """Return only order reconciliations that require review."""

    review = _get_review(db, location_id, review_date)
    return [
        schemas.AnalystReconciliationException(
            **order.model_dump(),
            currency=review.currency,
        )
        for order in review.orders
        if order.status == "REVIEW_REQUIRED"
    ]


def get_top_items(
    db: Session,
    location_id: int,
    review_date: date,
    limit: int = 5,
) -> list[schemas.AnalystTopItem]:
    """Rank items by quantity, net sales, then case-insensitive item name."""

    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise AnalystValidationError("limit must be a positive integer.")

    review = _get_review(db, location_id, review_date)
    order_ids = [order.order_id for order in review.orders]
    category_names_by_item: dict[str, set[str]] = {}
    if order_ids:
        item_categories = db.execute(
            select(
                models.OrderLineItem.item_name,
                models.OrderLineItem.category_name,
            )
            .where(models.OrderLineItem.order_id.in_(order_ids))
            .order_by(
                models.OrderLineItem.item_name,
                models.OrderLineItem.category_name,
            )
        ).all()
        for item_name, category_name in item_categories:
            if category_name is not None:
                category_names_by_item.setdefault(item_name, set()).add(
                    category_name
                )

    ranked_items = sorted(
        review.top_items,
        key=lambda item: (
            -item.quantity_sold,
            -item.total_sales_amount,
            item.item_name.casefold(),
            item.item_name,
        ),
    )
    ranked_results: list[schemas.AnalystTopItem] = []
    for rank, item in enumerate(ranked_items[:limit], start=1):
        category_names = category_names_by_item.get(item.item_name, set())
        ranked_results.append(
            schemas.AnalystTopItem(
                item_name=item.item_name,
                category_name=(
                    next(iter(category_names)) if len(category_names) == 1 else None
                ),
                currency=review.currency,
                quantity_sold=item.quantity_sold,
                sales_amount=item.total_sales_amount,
                rank=rank,
            )
        )
    return ranked_results


def get_refund_summary(
    db: Session,
    location_id: int,
    review_date: date,
) -> schemas.AnalystRefundSummary:
    """Summarize refunds linked to the selected day's orders."""

    review = _get_review(db, location_id, review_date)
    order_ids = [order.order_id for order in review.orders]
    refunds = (
        list(
            db.scalars(
                select(models.Refund)
                .join(models.Payment, models.Refund.payment_id == models.Payment.id)
                .where(models.Payment.order_id.in_(order_ids))
                .order_by(models.Refund.id)
            ).all()
        )
        if order_ids
        else []
    )
    payment_ids = {refund.payment_id for refund in refunds}
    payments = (
        list(
            db.scalars(
                select(models.Payment).where(models.Payment.id.in_(payment_ids))
            ).all()
        )
        if payment_ids
        else []
    )
    payments_by_id = {payment.id: payment for payment in payments}

    return schemas.AnalystRefundSummary(
        location_id=review.location_id,
        currency=review.currency,
        review_date=review.review_date,
        completed_refund_count=sum(
            refund.status == "COMPLETED" for refund in refunds
        ),
        completed_refund_amount=review.completed_refund_amount,
        pending_refund_count=sum(refund.status == "PENDING" for refund in refunds),
        failed_refund_count=sum(refund.status == "FAILED" for refund in refunds),
        refunds=[
            schemas.AnalystRefundDetail(
                refund_id=refund.id,
                square_refund_id=refund.square_refund_id,
                payment_id=refund.payment_id,
                square_payment_id=payments_by_id[refund.payment_id].square_payment_id,
                order_id=payments_by_id[refund.payment_id].order_id,
                status=refund.status,
                amount=refund.amount,
            )
            for refund in refunds
        ],
    )


def get_discount_summary(
    db: Session,
    location_id: int,
    review_date: date,
) -> schemas.AnalystDiscountSummary:
    """Summarize recorded order discounts without inferring discount types."""

    review = _get_review(db, location_id, review_date)
    order_ids = [order.order_id for order in review.orders]
    discounted_order_ids = (
        list(
            db.scalars(
                select(models.Order.id)
                .where(
                    models.Order.id.in_(order_ids),
                    models.Order.discount_amount > 0,
                )
                .order_by(models.Order.id)
            ).all()
        )
        if order_ids
        else []
    )
    return schemas.AnalystDiscountSummary(
        location_id=review.location_id,
        currency=review.currency,
        review_date=review.review_date,
        total_discount_amount=review.discount_amount,
        discounted_order_count=len(discounted_order_ids),
        order_count=review.order_count,
        discounted_order_percentage=(
            round(len(discounted_order_ids) * 100 / review.order_count, 2)
            if review.order_count
            else None
        ),
        discounted_order_ids=discounted_order_ids,
    )


def _percentage_change(value_a: int, value_b: int) -> float | None:
    if value_a == 0:
        return None
    return round((value_b - value_a) * 100 / value_a, 2)


def compare_daily_performance(
    db: Session,
    location_id: int,
    date_a: date,
    date_b: date,
) -> schemas.AnalystDailyComparison:
    """Compare deterministic daily metrics; changes are date B minus date A."""

    _validate_date(date_a, "date_a")
    _validate_date(date_b, "date_b")
    summary_a = get_daily_summary(db, location_id, date_a)
    summary_b = get_daily_summary(db, location_id, date_b)
    if summary_a.currency != summary_b.currency:
        raise AnalystValidationError(
            "Daily performance cannot compare dates with different currencies."
        )

    return schemas.AnalystDailyComparison(
        location_id=location_id,
        currency=summary_a.currency,
        date_a=date_a,
        date_b=date_b,
        order_total_amount_a=summary_a.order_total_amount,
        order_total_amount_b=summary_b.order_total_amount,
        order_total_change=summary_b.order_total_amount - summary_a.order_total_amount,
        order_total_percentage_change=_percentage_change(
            summary_a.order_total_amount, summary_b.order_total_amount
        ),
        net_collected_amount_a=summary_a.net_collected_amount,
        net_collected_amount_b=summary_b.net_collected_amount,
        net_collected_change=(
            summary_b.net_collected_amount - summary_a.net_collected_amount
        ),
        net_collected_percentage_change=_percentage_change(
            summary_a.net_collected_amount, summary_b.net_collected_amount
        ),
        order_count_a=summary_a.order_count,
        order_count_b=summary_b.order_count,
        order_count_change=summary_b.order_count - summary_a.order_count,
        average_order_value_a=summary_a.average_order_value,
        average_order_value_b=summary_b.average_order_value,
        average_order_value_change=(
            summary_b.average_order_value - summary_a.average_order_value
        ),
        completed_refund_amount_a=summary_a.completed_refund_amount,
        completed_refund_amount_b=summary_b.completed_refund_amount,
        refund_amount_change=(
            summary_b.completed_refund_amount - summary_a.completed_refund_amount
        ),
        discount_amount_a=summary_a.discount_amount,
        discount_amount_b=summary_b.discount_amount,
        discount_amount_change=summary_b.discount_amount - summary_a.discount_amount,
        reconciliation_status_a=summary_a.reconciliation_status,
        reconciliation_status_b=summary_b.reconciliation_status,
    )
