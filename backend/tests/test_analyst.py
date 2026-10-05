from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.services.analyst import AnalystValidationError, get_top_items


def _build_analyst_data(db: Session) -> tuple[int, list[models.Order]]:
    location = models.Location(
        name="Analyst Sushi",
        timezone="America/New_York",
        currency="USD",
    )
    first_order = models.Order(
        square_order_id="ANALYST-ORDER-1",
        location=location,
        state="COMPLETED",
        currency="USD",
        created_at=datetime(2026, 9, 14, 18, 0),
        subtotal_amount=3000,
        discount_amount=300,
        tax_amount=200,
        service_charge_amount=50,
        total_amount=2950,
        line_items=[
            models.OrderLineItem(
                item_name="Spicy Tuna Roll",
                category_name="Rolls",
                quantity=2,
                unit_price_amount=1000,
                gross_sales_amount=2000,
                discount_amount=100,
                total_amount=1900,
            ),
            models.OrderLineItem(
                item_name="Miso Soup",
                category_name="Sides",
                quantity=1,
                unit_price_amount=600,
                gross_sales_amount=600,
                discount_amount=0,
                total_amount=600,
            ),
        ],
    )
    first_order.payments = [
        models.Payment(
            square_payment_id="ANALYST-PAYMENT-1",
            status="COMPLETED",
            currency="USD",
            amount=3000,
            refunds=[
                models.Refund(
                    square_refund_id="ANALYST-REFUND-DONE",
                    status="COMPLETED",
                    currency="USD",
                    amount=100,
                ),
                models.Refund(
                    square_refund_id="ANALYST-REFUND-PENDING",
                    status="PENDING",
                    currency="USD",
                    amount=25,
                ),
                models.Refund(
                    square_refund_id="ANALYST-REFUND-FAILED",
                    status="FAILED",
                    currency="USD",
                    amount=10,
                ),
            ],
        )
    ]
    second_order = models.Order(
        square_order_id="ANALYST-ORDER-2",
        location=location,
        state="COMPLETED",
        currency="USD",
        created_at=datetime(2026, 9, 14, 19, 0),
        subtotal_amount=2000,
        discount_amount=0,
        tax_amount=160,
        service_charge_amount=0,
        total_amount=2160,
        line_items=[
            models.OrderLineItem(
                item_name="Spicy Tuna Roll",
                category_name="Rolls",
                quantity=1,
                unit_price_amount=1000,
                gross_sales_amount=1000,
                discount_amount=0,
                total_amount=1000,
            ),
            models.OrderLineItem(
                item_name="Miso Soup",
                category_name="Sides",
                quantity=1,
                unit_price_amount=700,
                gross_sales_amount=700,
                discount_amount=0,
                total_amount=700,
            ),
            models.OrderLineItem(
                item_name="Edamame",
                category_name="Sides",
                quantity=1,
                unit_price_amount=700,
                gross_sales_amount=700,
                discount_amount=0,
                total_amount=700,
            ),
            models.OrderLineItem(
                item_name="Avocado Roll",
                category_name="Rolls",
                quantity=1,
                unit_price_amount=700,
                gross_sales_amount=700,
                discount_amount=0,
                total_amount=700,
            ),
        ],
    )
    second_order.payments = [
        models.Payment(
            square_payment_id="ANALYST-PAYMENT-2",
            status="COMPLETED",
            currency="USD",
            amount=2160,
        )
    ]
    third_order = models.Order(
        square_order_id="ANALYST-ORDER-3",
        location=location,
        state="COMPLETED",
        currency="USD",
        created_at=datetime(2026, 9, 14, 20, 0),
        subtotal_amount=500,
        discount_amount=50,
        tax_amount=40,
        service_charge_amount=0,
        total_amount=490,
        line_items=[
            models.OrderLineItem(
                item_name="Miso Soup",
                category_name="Sides",
                quantity=1,
                unit_price_amount=600,
                gross_sales_amount=600,
                discount_amount=50,
                total_amount=550,
            )
        ],
    )
    third_order.payments = [
        models.Payment(
            square_payment_id="ANALYST-PAYMENT-3",
            status="COMPLETED",
            currency="USD",
            amount=490,
        )
    ]
    clean_order = models.Order(
        square_order_id="ANALYST-ORDER-CLEAN",
        location=location,
        state="COMPLETED",
        currency="USD",
        created_at=datetime(2026, 9, 16, 18, 0),
        subtotal_amount=1000,
        discount_amount=0,
        tax_amount=0,
        service_charge_amount=0,
        total_amount=1000,
        line_items=[
            models.OrderLineItem(
                item_name="Dragon Roll",
                category_name="Rolls",
                quantity=1,
                unit_price_amount=1000,
                gross_sales_amount=1000,
                discount_amount=0,
                total_amount=1000,
            )
        ],
    )
    clean_order.payments = [
        models.Payment(
            square_payment_id="ANALYST-PAYMENT-CLEAN",
            status="COMPLETED",
            currency="USD",
            amount=1000,
        )
    ]

    db.add_all([first_order, second_order, third_order, clean_order])
    db.commit()
    return location.id, [first_order, second_order, third_order]


def test_daily_summary_matches_daily_review(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, _ = _build_analyst_data(db_session)
    params = {"location_id": location_id, "date": "2026-09-14"}

    review = client.get("/api/daily-review", params=params)
    summary = client.get("/api/analyst/daily-summary", params=params)

    assert review.status_code == summary.status_code == 200
    expected = review.json()
    actual = summary.json()
    assert {
        key: actual[key]
        for key in (
            "location_id",
            "currency",
            "review_date",
            "order_count",
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "service_charge_amount",
            "order_total_amount",
            "completed_payment_amount",
            "completed_refund_amount",
            "net_collected_amount",
            "average_order_value",
            "reconciliation_difference",
            "reconciliation_status",
        )
    } == {
        key: expected[key]
        for key in (
            "location_id",
            "currency",
            "review_date",
            "order_count",
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "service_charge_amount",
            "order_total_amount",
            "completed_payment_amount",
            "completed_refund_amount",
            "net_collected_amount",
            "average_order_value",
            "reconciliation_difference",
            "reconciliation_status",
        )
    }


def test_reconciliation_exceptions_returns_only_mismatched_orders(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, orders = _build_analyst_data(db_session)

    response = client.get(
        "/api/analyst/reconciliation-exceptions",
        params={"location_id": location_id, "date": "2026-09-14"},
    )

    assert response.status_code == 200
    assert [order["order_id"] for order in response.json()] == [orders[0].id]
    assert response.json()[0]["difference"] == -50
    assert response.json()[0]["status"] == "REVIEW_REQUIRED"


def test_clean_reconciled_date_has_no_exceptions(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, _ = _build_analyst_data(db_session)

    response = client.get(
        "/api/analyst/reconciliation-exceptions",
        params={"location_id": location_id, "date": "2026-09-16"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_top_items_order_is_deterministic_and_includes_category(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, _ = _build_analyst_data(db_session)

    response = client.get(
        "/api/analyst/top-items",
        params={"location_id": location_id, "date": "2026-09-14"},
    )

    assert response.status_code == 200
    items = response.json()
    assert [item["item_name"] for item in items] == [
        "Spicy Tuna Roll",
        "Miso Soup",
        "Avocado Roll",
        "Edamame",
    ]
    assert [item["rank"] for item in items] == [1, 2, 3, 4]
    assert items[0]["quantity_sold"] == 3
    assert items[0]["sales_amount"] == 2900
    assert items[0]["category_name"] == "Rolls"
    assert items[1]["quantity_sold"] == 3
    assert items[2]["sales_amount"] == items[3]["sales_amount"] == 700


def test_top_items_limit_is_respected(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, _ = _build_analyst_data(db_session)

    response = client.get(
        "/api/analyst/top-items",
        params={"location_id": location_id, "date": "2026-09-14", "limit": 2},
    )

    assert response.status_code == 200
    assert [item["rank"] for item in response.json()] == [1, 2]
    assert len(response.json()) == 2


def test_top_items_rejects_nonpositive_service_limit(
    db_session: Session,
) -> None:
    location = models.Location(name="Invalid Analyst Limit")
    db_session.add(location)
    db_session.commit()

    with pytest.raises(AnalystValidationError, match="positive integer"):
        get_top_items(db_session, location.id, datetime(2026, 9, 14).date(), 0)


def test_refund_summary_excludes_pending_and_failed_from_completed_total(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, orders = _build_analyst_data(db_session)

    response = client.get(
        "/api/analyst/refunds",
        params={"location_id": location_id, "date": "2026-09-14"},
    )

    assert response.status_code == 200
    refund_summary = response.json()
    assert refund_summary["completed_refund_count"] == 1
    assert refund_summary["completed_refund_amount"] == 100
    assert refund_summary["pending_refund_count"] == 1
    assert refund_summary["failed_refund_count"] == 1
    assert {refund["status"] for refund in refund_summary["refunds"]} == {
        "COMPLETED",
        "PENDING",
        "FAILED",
    }
    assert all(refund["order_id"] == orders[0].id for refund in refund_summary["refunds"])


def test_discount_summary_reports_only_stored_order_discounts(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, orders = _build_analyst_data(db_session)

    response = client.get(
        "/api/analyst/discounts",
        params={"location_id": location_id, "date": "2026-09-14"},
    )

    assert response.status_code == 200
    discounts = response.json()
    assert discounts["total_discount_amount"] == 350
    assert discounts["discounted_order_count"] == 2
    assert discounts["order_count"] == 3
    assert discounts["discounted_order_percentage"] == 66.67
    assert discounts["discounted_order_ids"] == [orders[0].id, orders[2].id]


def test_compare_two_populated_dates(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, _ = _build_analyst_data(db_session)

    response = client.get(
        "/api/analyst/compare",
        params={
            "location_id": location_id,
            "date_a": "2026-09-14",
            "date_b": "2026-09-16",
        },
    )

    assert response.status_code == 200
    comparison = response.json()
    assert comparison["order_total_amount_a"] == 5600
    assert comparison["order_total_amount_b"] == 1000
    assert comparison["order_total_change"] == -4600
    assert comparison["net_collected_amount_a"] == 5550
    assert comparison["net_collected_amount_b"] == 1000
    assert comparison["net_collected_change"] == -4550
    assert comparison["order_count_change"] == -2
    assert comparison["average_order_value_a"] == 1867
    assert comparison["average_order_value_b"] == 1000
    assert comparison["refund_amount_change"] == -100
    assert comparison["discount_amount_change"] == -350
    assert comparison["reconciliation_status_a"] == "REVIEW_REQUIRED"
    assert comparison["reconciliation_status_b"] == "RECONCILED"


def test_compare_populated_and_empty_date(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, _ = _build_analyst_data(db_session)

    response = client.get(
        "/api/analyst/compare",
        params={
            "location_id": location_id,
            "date_a": "2026-09-14",
            "date_b": "2026-09-15",
        },
    )

    assert response.status_code == 200
    comparison = response.json()
    assert comparison["order_count_b"] == 0
    assert comparison["order_total_amount_b"] == 0
    assert comparison["net_collected_amount_b"] == 0
    assert comparison["order_total_change"] == -5600
    assert comparison["net_collected_change"] == -5550
    assert comparison["reconciliation_status_b"] == "RECONCILED"


def test_compare_percentage_change_is_null_for_zero_baseline(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, _ = _build_analyst_data(db_session)

    response = client.get(
        "/api/analyst/compare",
        params={
            "location_id": location_id,
            "date_a": "2026-09-15",
            "date_b": "2026-09-16",
        },
    )

    assert response.status_code == 200
    comparison = response.json()
    assert comparison["order_total_percentage_change"] is None
    assert comparison["net_collected_percentage_change"] is None


def test_analyst_endpoints_reject_nonexistent_location(client: TestClient) -> None:
    response = client.get(
        "/api/analyst/daily-summary",
        params={"location_id": 999, "date": "2026-09-14"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Location not found."


def test_analyst_endpoints_reject_invalid_dates(client: TestClient) -> None:
    response = client.get(
        "/api/analyst/daily-summary",
        params={"location_id": 1, "date": "not-a-date"},
    )

    assert response.status_code == 422


def test_analyst_reads_do_not_mutate_ledger(
    client: TestClient,
    db_session: Session,
) -> None:
    location_id, _ = _build_analyst_data(db_session)
    before = {
        model.__tablename__: db_session.scalar(
            select(func.count()).select_from(model)
        )
        for model in (models.Order, models.OrderLineItem, models.Payment, models.Refund)
    }

    for endpoint, params in (
        ("/api/analyst/daily-summary", {"date": "2026-09-14"}),
        ("/api/analyst/reconciliation-exceptions", {"date": "2026-09-14"}),
        ("/api/analyst/top-items", {"date": "2026-09-14"}),
        ("/api/analyst/refunds", {"date": "2026-09-14"}),
        ("/api/analyst/discounts", {"date": "2026-09-14"}),
        (
            "/api/analyst/compare",
            {"date_a": "2026-09-14", "date_b": "2026-09-16"},
        ),
    ):
        response = client.get(
            endpoint,
            params={"location_id": location_id, **params},
        )
        assert response.status_code == 200

    after = {
        model.__tablename__: db_session.scalar(
            select(func.count()).select_from(model)
        )
        for model in (models.Order, models.OrderLineItem, models.Payment, models.Refund)
    }
    assert after == before
