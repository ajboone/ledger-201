import argparse
from datetime import datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import models, schemas
from app.database import Base, DATABASE_URL, engine as app_engine
from app.services.orders import create_order
from app.services.payments import create_payment, create_refund


DEMO_LOCATION_NAME = "Sushi 201"
DEMO_SQUARE_LOCATION_ID = "LEDGER201-DEMO-SUSHI201"


def _line_item(
    item_name: str,
    quantity: int,
    unit_price_amount: int,
    category_name: str,
) -> schemas.OrderLineItemCreate:
    gross_sales_amount = quantity * unit_price_amount
    return schemas.OrderLineItemCreate(
        item_name=item_name,
        category_name=category_name,
        quantity=quantity,
        unit_price_amount=unit_price_amount,
        gross_sales_amount=gross_sales_amount,
        total_amount=gross_sales_amount,
    )


def _demo_orders(location_id: int) -> tuple[schemas.OrderCreate, ...]:
    return (
        schemas.OrderCreate(
            location_id=location_id,
            square_order_id="LEDGER201-DEMO-ORDER-001",
            state="COMPLETED",
            currency="USD",
            created_at=datetime.fromisoformat("2026-09-12T18:15:00-04:00"),
            closed_at=datetime.fromisoformat("2026-09-12T18:42:00-04:00"),
            subtotal_amount=1597,
            tax_amount=128,
            total_amount=1725,
            line_items=[
                _line_item("California", 1, 699, "Sushi Rolls"),
                _line_item("Miso Soup", 1, 299, "Salads & Soups"),
                _line_item("Edamame", 1, 599, "Appetizers"),
            ],
        ),
        schemas.OrderCreate(
            location_id=location_id,
            square_order_id="LEDGER201-DEMO-ORDER-002",
            state="COMPLETED",
            currency="USD",
            created_at=datetime.fromisoformat("2026-09-13T19:05:00-04:00"),
            closed_at=datetime.fromisoformat("2026-09-13T19:38:00-04:00"),
            subtotal_amount=4294,
            discount_amount=300,
            tax_amount=320,
            total_amount=4314,
            line_items=[
                _line_item("California", 2, 699, "Sushi Rolls"),
                _line_item("Spicy Tuna Roll", 1, 899, "Sushi Rolls"),
                _line_item("Dragon Roll", 1, 999, "Sushi Rolls"),
                _line_item("Pork Gyoza 6pc", 1, 699, "Appetizers"),
                _line_item("House Salad", 1, 299, "Salads & Soups"),
            ],
        ),
        schemas.OrderCreate(
            location_id=location_id,
            square_order_id="LEDGER201-DEMO-ORDER-003",
            state="COMPLETED",
            currency="USD",
            created_at=datetime.fromisoformat("2026-09-14T20:10:00-04:00"),
            closed_at=datetime.fromisoformat("2026-09-14T20:51:00-04:00"),
            subtotal_amount=5496,
            discount_amount=500,
            tax_amount=400,
            total_amount=5396,
            line_items=[
                _line_item("Sashimi Meal", 1, 3399, "Sushi Entrées"),
                _line_item("Spicy Tuna Roll", 1, 899, "Sushi Rolls"),
                _line_item("Edamame", 1, 599, "Appetizers"),
                _line_item("Fried Cheesecake", 1, 599, "Desserts"),
            ],
        ),
        schemas.OrderCreate(
            location_id=location_id,
            square_order_id="LEDGER201-DEMO-ORDER-004",
            state="COMPLETED",
            currency="USD",
            created_at=datetime.fromisoformat("2026-09-16T17:50:00-04:00"),
            closed_at=datetime.fromisoformat("2026-09-16T18:22:00-04:00"),
            subtotal_amount=6496,
            tax_amount=520,
            total_amount=7016,
            line_items=[
                _line_item("Hibachi Steak", 1, 2099, "Hibachi Entrées"),
                _line_item("Hibachi Shrimp", 1, 1599, "Hibachi Entrées"),
                _line_item("Teriyaki Chicken", 1, 1499, "Hibachi Entrées"),
                _line_item(
                    "Shrimp & Vegetable Tempura",
                    1,
                    1299,
                    "Appetizers",
                ),
            ],
        ),
    )


def seed_demo_data(db: Session) -> tuple[int, int]:
    """Create missing deterministic Sushi 201 demo records without deleting data."""

    location = db.scalar(
        select(models.Location).where(
            models.Location.square_location_id == DEMO_SQUARE_LOCATION_ID
        )
    )
    if location is None:
        location = db.scalar(
            select(models.Location).where(
                func.lower(models.Location.name) == DEMO_LOCATION_NAME.lower()
            )
        )
    if location is None:
        location = models.Location(
            name=DEMO_LOCATION_NAME,
            square_location_id=DEMO_SQUARE_LOCATION_ID,
            timezone="America/New_York",
            currency="USD",
        )
        db.add(location)
        db.commit()
        db.refresh(location)

    inserted_orders = 0
    skipped_orders = 0
    for order_data in _demo_orders(location.id):
        order = db.scalar(
            select(models.Order).where(
                models.Order.square_order_id == order_data.square_order_id
            )
        )
        if order is None:
            create_order(db, order_data)
            inserted_orders += 1
            continue

        _refresh_demo_order(db, order, order_data)
        skipped_orders += 1

    _seed_demo_payments_and_refunds(db)
    return inserted_orders, skipped_orders


def _refresh_demo_order(
    db: Session,
    order: models.Order,
    order_data: schemas.OrderCreate,
) -> None:
    """Refresh only the known demo order and its existing seeded line items."""

    existing_line_items = list(
        db.scalars(
            select(models.OrderLineItem)
            .where(models.OrderLineItem.order_id == order.id)
            .order_by(models.OrderLineItem.id)
        ).all()
    )
    if len(existing_line_items) != len(order_data.line_items):
        raise RuntimeError(
            f"Demo order {order.square_order_id} has a different line-item count "
            "than its deterministic fixture; refusing to delete or reset records."
        )

    order.state = order_data.state
    order.currency = order_data.currency
    order.created_at = order_data.created_at
    order.closed_at = order_data.closed_at
    order.subtotal_amount = order_data.subtotal_amount
    order.discount_amount = order_data.discount_amount
    order.tax_amount = order_data.tax_amount
    order.service_charge_amount = order_data.service_charge_amount
    order.total_amount = order_data.total_amount

    for existing, fixture in zip(existing_line_items, order_data.line_items):
        existing.square_line_item_id = fixture.square_line_item_id
        existing.catalog_object_id = fixture.catalog_object_id
        existing.item_name = fixture.item_name
        existing.variation_name = fixture.variation_name
        existing.category_name = fixture.category_name
        existing.quantity = fixture.quantity
        existing.unit_price_amount = fixture.unit_price_amount
        existing.gross_sales_amount = fixture.gross_sales_amount
        existing.discount_amount = fixture.discount_amount
        existing.total_amount = fixture.total_amount

    db.commit()


def _seed_demo_payments_and_refunds(db: Session) -> None:
    """Add deterministic payment/refund examples for the seeded demo orders."""

    payment_examples = (
        (
            "LEDGER201-DEMO-PAYMENT-001",
            "LEDGER201-DEMO-ORDER-001",
            "COMPLETED",
            "CARD",
            1725,
            "2026-09-12T18:42:00-04:00",
        ),
        (
            "LEDGER201-DEMO-PAYMENT-002",
            "LEDGER201-DEMO-ORDER-002",
            "COMPLETED",
            "CASH",
            4314,
            "2026-09-13T19:38:00-04:00",
        ),
        (
            "LEDGER201-DEMO-PAYMENT-003",
            "LEDGER201-DEMO-ORDER-003",
            "COMPLETED",
            "CARD",
            5396,
            "2026-09-14T20:51:00-04:00",
        ),
        (
            "LEDGER201-DEMO-PAYMENT-004",
            "LEDGER201-DEMO-ORDER-004",
            "COMPLETED",
            "CARD",
            7016,
            "2026-09-16T18:22:00-04:00",
        ),
        (
            "LEDGER201-DEMO-PAYMENT-005",
            "LEDGER201-DEMO-ORDER-001",
            "FAILED",
            "CARD",
            1200,
            "2026-09-12T18:40:00-04:00",
        ),
    )

    for payment_id, order_square_id, payment_status, source_type, amount, created_at in payment_examples:
        payment = db.scalar(
            select(models.Payment).where(
                models.Payment.square_payment_id == payment_id
            )
        )
        order = db.scalar(
            select(models.Order).where(
                models.Order.square_order_id == order_square_id
            )
        )
        if order is None:
            raise RuntimeError(
                f"Demo order {order_square_id} was not found while seeding payments."
            )
        if payment is not None:
            if payment.order_id != order.id:
                raise RuntimeError(
                    f"Demo payment {payment_id} is associated with an unexpected order."
                )
            payment.amount = amount
            payment.currency = order.currency
            continue

        create_payment(
            db,
            schemas.PaymentCreate(
                order_id=order.id,
                square_payment_id=payment_id,
                status=payment_status,
                source_type=source_type,
                currency=order.currency,
                amount=amount,
                created_at=datetime.fromisoformat(created_at),
            ),
        )

    db.commit()

    payment = db.scalar(
        select(models.Payment).where(
            models.Payment.square_payment_id == "LEDGER201-DEMO-PAYMENT-003"
        )
    )
    if payment is None:
        raise RuntimeError("Demo payment 003 was not found while seeding refunds.")

    refund_examples = (
        (
            "LEDGER201-DEMO-REFUND-001",
            "COMPLETED",
            724,
            "Partial item refund",
            "2026-09-14T21:10:00-04:00",
        ),
        (
            "LEDGER201-DEMO-REFUND-002",
            "PENDING",
            200,
            "Refund awaiting processor confirmation",
            "2026-09-14T21:12:00-04:00",
        ),
        (
            "LEDGER201-DEMO-REFUND-003",
            "FAILED",
            100,
            "Example declined refund attempt",
            "2026-09-14T21:15:00-04:00",
        ),
    )

    for refund_id, refund_status, amount, reason, created_at in refund_examples:
        existing_refund = db.scalar(
            select(models.Refund).where(
                models.Refund.square_refund_id == refund_id
            )
        )
        if existing_refund is not None:
            continue

        create_refund(
            db,
            schemas.RefundCreate(
                payment_id=payment.id,
                square_refund_id=refund_id,
                status=refund_status,
                currency=payment.currency,
                amount=amount,
                reason=reason,
                created_at=datetime.fromisoformat(created_at),
            ),
        )


def _engine_for_database(database_url: str) -> Engine:
    if database_url == DATABASE_URL:
        return app_engine

    connect_args = (
        {"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {}
    )

    return create_engine(database_url, connect_args=connect_args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Ledger 201 demo orders.")
    parser.add_argument(
        "--database-url",
        default=DATABASE_URL,
        help="Optional SQLAlchemy URL; defaults to the configured local database.",
    )
    arguments = parser.parse_args()

    target_engine = _engine_for_database(arguments.database_url)
    Base.metadata.create_all(bind=target_engine)
    session_factory = sessionmaker(
        bind=target_engine,
        autoflush=False,
        autocommit=False,
    )

    with session_factory() as db:
        inserted_orders, skipped_orders = seed_demo_data(db)
        payment_count = db.scalar(
            select(func.count()).select_from(models.Payment).where(
                models.Payment.square_payment_id.like("LEDGER201-DEMO-PAYMENT-%")
            )
        )
        refund_count = db.scalar(
            select(func.count()).select_from(models.Refund).where(
                models.Refund.square_refund_id.like("LEDGER201-DEMO-REFUND-%")
            )
        )

    print(
        f"Demo seed complete: {inserted_orders} orders created, "
        f"{skipped_orders} existing orders reused; "
        f"{payment_count} demo payments and {refund_count} demo refunds present."
    )


if __name__ == "__main__":
    main()
