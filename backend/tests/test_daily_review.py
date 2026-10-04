from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models


def _build_review_data(db: Session) -> tuple[int, list[models.Order]]:
    location = models.Location(
        name="Sushi 201 Review",
        timezone="America/New_York",
        currency="USD",
    )
    first_order = models.Order(
        square_order_id="REVIEW-ORDER-1",
        location=location,
        state="COMPLETED",
        currency="USD",
        created_at=datetime(2026, 9, 14, 18, 0),
        subtotal_amount=3000,
        discount_amount=100,
        tax_amount=200,
        service_charge_amount=50,
        total_amount=3150,
        line_items=[
            models.OrderLineItem(
                item_name="Spicy Tuna Roll",
                quantity=2,
                unit_price_amount=1200,
                gross_sales_amount=2400,
                discount_amount=100,
                total_amount=2300,
            ),
            models.OrderLineItem(
                item_name="Miso Soup",
                quantity=1,
                unit_price_amount=600,
                gross_sales_amount=600,
                discount_amount=0,
                total_amount=600,
            ),
        ],
    )
    second_order = models.Order(
        square_order_id="REVIEW-ORDER-2",
        location=location,
        state="COMPLETED",
        currency="USD",
        created_at=datetime(2026, 9, 14, 21, 0),
        subtotal_amount=2000,
        discount_amount=0,
        tax_amount=160,
        service_charge_amount=0,
        total_amount=2160,
        line_items=[
            models.OrderLineItem(
                item_name="Spicy Tuna Roll",
                quantity=1,
                unit_price_amount=1200,
                gross_sales_amount=1200,
                discount_amount=0,
                total_amount=1200,
            ),
            models.OrderLineItem(
                item_name="Edamame",
                quantity=1,
                unit_price_amount=800,
                gross_sales_amount=800,
                discount_amount=0,
                total_amount=800,
            ),
        ],
    )
    next_day_order = models.Order(
        square_order_id="REVIEW-ORDER-NEXT-DAY",
        location=location,
        state="COMPLETED",
        currency="USD",
        created_at=datetime(2026, 9, 15, 0, 0),
        subtotal_amount=1000,
        discount_amount=0,
        tax_amount=80,
        service_charge_amount=0,
        total_amount=1080,
    )
    first_order.payments = [
        models.Payment(
            square_payment_id="REVIEW-PAY-1",
            status="COMPLETED",
            currency="USD",
            amount=3300,
            refunds=[
                models.Refund(
                    square_refund_id="REVIEW-REFUND-COMPLETED",
                    status="COMPLETED",
                    currency="USD",
                    amount=150,
                ),
                models.Refund(
                    square_refund_id="REVIEW-REFUND-PENDING",
                    status="PENDING",
                    currency="USD",
                    amount=100,
                ),
                models.Refund(
                    square_refund_id="REVIEW-REFUND-FAILED",
                    status="FAILED",
                    currency="USD",
                    amount=50,
                ),
            ],
        ),
        models.Payment(
            square_payment_id="REVIEW-PAY-FAILED",
            status="FAILED",
            currency="USD",
            amount=900,
        ),
        models.Payment(
            square_payment_id="REVIEW-PAY-PENDING",
            status="PENDING",
            currency="USD",
            amount=800,
        ),
    ]
    second_order.payments = [
        models.Payment(
            square_payment_id="REVIEW-PAY-2",
            status="COMPLETED",
            currency="USD",
            amount=2160,
        )
    ]

    db.add_all([first_order, second_order, next_day_order])
    db.commit()
    return location.id, [first_order, second_order]


def test_daily_review_calculates_daily_totals_statuses_and_average(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, orders = _build_review_data(db_session)

    response = client.get(
        "/api/daily-review",
        params={"location_id": location_id, "date": "2026-09-14"},
    )

    assert response.status_code == 200
    review = response.json()
    assert review["location_id"] == location_id
    assert review["review_date"] == "2026-09-14"
    assert review["order_count"] == 2
    assert review["subtotal_amount"] == 5000
    assert review["discount_amount"] == 100
    assert review["tax_amount"] == 360
    assert review["service_charge_amount"] == 50
    assert review["order_total_amount"] == 5310
    assert review["completed_payment_amount"] == 5460
    assert review["completed_refund_amount"] == 150
    assert review["net_collected_amount"] == 5310
    assert review["average_order_value"] == 2655
    assert review["reconciliation_difference"] == 0
    assert review["reconciliation_status"] == "RECONCILED"
    assert [order["order_id"] for order in review["orders"]] == [
        order.id for order in orders
    ]
    assert all(order["status"] == "RECONCILED" for order in review["orders"])


def test_daily_review_identifies_mismatched_order(client: TestClient) -> None:
    location = client.post(
        "/api/locations",
        json={
            "name": "Mismatch Location",
            "timezone": "America/New_York",
            "currency": "USD",
        },
    ).json()
    order = client.post(
        "/api/orders",
        json={
            "location_id": location["id"],
            "square_order_id": "MISMATCH-ORDER",
            "created_at": "2026-09-14T12:00:00-04:00",
            "subtotal_amount": 1000,
            "total_amount": 1000,
        },
    ).json()
    client.post(
        "/api/payments",
        json={
            "order_id": order["id"],
            "square_payment_id": "MISMATCH-PAYMENT",
            "status": "COMPLETED",
            "currency": "USD",
            "amount": 900,
        },
    )

    response = client.get(
        "/api/daily-review",
        params={"location_id": location["id"], "date": "2026-09-14"},
    )

    assert response.status_code == 200
    review = response.json()
    assert review["reconciliation_status"] == "REVIEW_REQUIRED"
    assert review["reconciliation_difference"] == -100
    assert review["orders"][0]["order_id"] == order["id"]
    assert review["orders"][0]["difference"] == -100
    assert review["orders"][0]["status"] == "REVIEW_REQUIRED"


def test_daily_review_top_items_aggregate_quantity_and_sales(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, _ = _build_review_data(db_session)
    response = client.get(
        "/api/daily-review",
        params={"location_id": location_id, "date": "2026-09-14"},
    )

    assert response.status_code == 200
    assert response.json()["top_items"] == [
        {
            "item_name": "Spicy Tuna Roll",
            "quantity_sold": 3,
            "gross_sales_amount": 3600,
            "total_sales_amount": 3500,
        },
        {
            "item_name": "Edamame",
            "quantity_sold": 1,
            "gross_sales_amount": 800,
            "total_sales_amount": 800,
        },
        {
            "item_name": "Miso Soup",
            "quantity_sold": 1,
            "gross_sales_amount": 600,
            "total_sales_amount": 600,
        },
    ]


def test_daily_review_empty_date_returns_zero_summary(client: TestClient) -> None:
    location = client.post(
        "/api/locations",
        json={"name": "Empty Day"},
    ).json()

    response = client.get(
        "/api/daily-review",
        params={"location_id": location["id"], "date": "2026-09-14"},
    )

    assert response.status_code == 200
    review = response.json()
    assert review["order_count"] == 0
    assert review["order_total_amount"] == 0
    assert review["net_collected_amount"] == 0
    assert review["average_order_value"] == 0
    assert review["reconciliation_status"] == "RECONCILED"
    assert review["orders"] == []
    assert review["top_items"] == []


def test_daily_review_rejects_unknown_location(client: TestClient) -> None:
    response = client.get(
        "/api/daily-review",
        params={"location_id": 999, "date": "2026-09-14"},
    )

    assert response.status_code == 404


def test_daily_review_rejects_mixed_order_currency(
    client: TestClient,
    db_session: Session,
) -> None:
    location = models.Location(name="Mixed Currency", currency="USD")
    db_session.add(location)
    db_session.flush()
    db_session.add(
        models.Order(
            location_id=location.id,
            state="COMPLETED",
            currency="CAD",
            created_at=datetime(2026, 9, 14, 12, 0),
            subtotal_amount=100,
            discount_amount=0,
            tax_amount=0,
            service_charge_amount=0,
            total_amount=100,
        )
    )
    db_session.commit()

    response = client.get(
        "/api/daily-review",
        params={"location_id": location.id, "date": "2026-09-14"},
    )

    assert response.status_code == 422


def test_daily_review_requires_valid_date(client: TestClient) -> None:
    location = client.post(
        "/api/locations",
        json={"name": "Invalid Date"},
    ).json()

    response = client.get(
        "/api/daily-review",
        params={"location_id": location["id"], "date": "not-a-date"},
    )

    assert response.status_code == 422
