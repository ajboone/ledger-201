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
            subtotal_amount=4600,
            discount_amount=200,
            tax_amount=352,
            total_amount=4752,
            line_items=[
                _line_item("Spicy Tuna Roll", 2, 1400, "Sushi Rolls"),
                _line_item("Edamame", 1, 800, "Appetizers"),
                _line_item("Soft Drink", 2, 500, "Beverages"),
            ],
        ),
        schemas.OrderCreate(
            location_id=location_id,
            square_order_id="LEDGER201-DEMO-ORDER-002",
            state="COMPLETED",
            currency="USD",
            created_at=datetime.fromisoformat("2026-09-13T19:05:00-04:00"),
            closed_at=datetime.fromisoformat("2026-09-13T19:38:00-04:00"),
            subtotal_amount=6700,
            tax_amount=536,
            total_amount=7236,
            line_items=[
                _line_item("Shrimp Tempura", 1, 1800, "Entrees"),
                _line_item("California Roll", 2, 1200, "Sushi Rolls"),
                _line_item("Salmon Nigiri", 4, 350, "Nigiri"),
                _line_item("Miso Soup", 1, 600, "Appetizers"),
                _line_item("Soft Drink", 1, 500, "Beverages"),
            ],
        ),
        schemas.OrderCreate(
            location_id=location_id,
            square_order_id="LEDGER201-DEMO-ORDER-003",
            state="COMPLETED",
            currency="USD",
            created_at=datetime.fromisoformat("2026-09-14T20:10:00-04:00"),
            closed_at=datetime.fromisoformat("2026-09-14T20:51:00-04:00"),
            subtotal_amount=5800,
            discount_amount=500,
            tax_amount=424,
            total_amount=5724,
            line_items=[
                _line_item("Sashimi Combo", 1, 3200, "Sashimi"),
                _line_item("Spicy Tuna Roll", 1, 1400, "Sushi Rolls"),
                _line_item("Miso Soup", 1, 600, "Appetizers"),
                _line_item("Edamame", 1, 600, "Appetizers"),
            ],
        ),
        schemas.OrderCreate(
            location_id=location_id,
            square_order_id="LEDGER201-DEMO-ORDER-004",
            state="COMPLETED",
            currency="USD",
            created_at=datetime.fromisoformat("2026-09-16T17:50:00-04:00"),
            closed_at=datetime.fromisoformat("2026-09-16T18:22:00-04:00"),
            subtotal_amount=3900,
            tax_amount=312,
            total_amount=4212,
            line_items=[
                _line_item("Shrimp Tempura", 1, 1800, "Entrees"),
                _line_item("Salmon Nigiri", 2, 350, "Nigiri"),
                _line_item("Miso Soup", 1, 600, "Appetizers"),
                _line_item("Edamame", 1, 800, "Appetizers"),
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
        existing_order = db.scalar(
            select(models.Order).where(
                models.Order.square_order_id == order_data.square_order_id
            )
        )
        if existing_order is not None:
            skipped_orders += 1
            continue

        create_order(db, order_data)
        inserted_orders += 1

    _seed_demo_payments_and_refunds(db)
    return inserted_orders, skipped_orders


def _seed_demo_payments_and_refunds(db: Session) -> None:
    """Add deterministic payment/refund examples for the seeded demo orders."""

    payment_examples = (
        (
            "LEDGER201-DEMO-PAYMENT-001",
            "LEDGER201-DEMO-ORDER-001",
            "COMPLETED",
            "CARD",
            4752,
            "2026-09-12T18:42:00-04:00",
        ),
        (
            "LEDGER201-DEMO-PAYMENT-002",
            "LEDGER201-DEMO-ORDER-002",
            "COMPLETED",
            "CASH",
            7236,
            "2026-09-13T19:38:00-04:00",
        ),
        (
            "LEDGER201-DEMO-PAYMENT-003",
            "LEDGER201-DEMO-ORDER-003",
            "COMPLETED",
            "CARD",
            5724,
            "2026-09-14T20:51:00-04:00",
        ),
        (
            "LEDGER201-DEMO-PAYMENT-004",
            "LEDGER201-DEMO-ORDER-004",
            "COMPLETED",
            "CARD",
            4212,
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
        existing_payment = db.scalar(
            select(models.Payment).where(
                models.Payment.square_payment_id == payment_id
            )
        )
        if existing_payment is not None:
            continue

        order = db.scalar(
            select(models.Order).where(
                models.Order.square_order_id == order_square_id
            )
        )
        if order is None:
            raise RuntimeError(
                f"Demo order {order_square_id} was not found while seeding payments."
            )

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
