from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.demo.seed import seed_demo_data
from app.services.orders import create_order


def test_create_order_with_line_items(client: TestClient) -> None:
    location_response = client.post(
        "/api/locations",
        json={"name": "Sushi 201"},
    )

    assert location_response.status_code == 201
    location_id = location_response.json()["id"]

    response = client.post(
        "/api/orders",
        json={
            "location_id": location_id,
            "square_order_id": "SQ-ORDER-123",
            "state": "COMPLETED",
            "currency": "usd",
            "created_at": "2024-01-01T12:00:00-05:00",
            "closed_at": "2024-01-01T12:05:00-05:00",
            "subtotal_amount": 3200,
            "discount_amount": 200,
            "tax_amount": 250,
            "service_charge_amount": 0,
            "total_amount": 3250,
            "line_items": [
                {
                    "square_line_item_id": "SQ-LINE-1",
                    "item_name": "Spicy Tuna Roll",
                    "quantity": 2,
                    "unit_price_amount": 1400,
                    "gross_sales_amount": 2800,
                    "discount_amount": 0,
                    "total_amount": 2800,
                },
                {
                    "item_name": "Miso Soup",
                    "quantity": 1,
                    "unit_price_amount": 400,
                    "gross_sales_amount": 400,
                    "total_amount": 400,
                },
            ],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["location_id"] == location_id
    assert payload["currency"] == "USD"
    assert payload["square_order_id"] == "SQ-ORDER-123"
    assert payload["line_items"][0]["item_name"] == "Spicy Tuna Roll"
    assert payload["line_items"][0]["quantity"] == 2


def test_duplicate_square_order_id_returns_conflict(client: TestClient) -> None:
    location_response = client.post(
        "/api/locations",
        json={"name": "Downtown"},
    )
    location_id = location_response.json()["id"]

    client.post(
        "/api/orders",
        json={
            "location_id": location_id,
            "square_order_id": "SQ-ORDER-REF",
            "subtotal_amount": 1000,
            "total_amount": 1000,
            "line_items": [
                {
                    "item_name": "Miso Soup",
                    "quantity": 1,
                    "unit_price_amount": 1000,
                    "gross_sales_amount": 1000,
                    "total_amount": 1000,
                }
            ],
        },
    )

    response = client.post(
        "/api/orders",
        json={
            "location_id": location_id,
            "square_order_id": "SQ-ORDER-REF",
            "subtotal_amount": 2000,
            "total_amount": 2000,
            "line_items": [
                {
                    "item_name": "Edamame",
                    "quantity": 1,
                    "unit_price_amount": 2000,
                    "gross_sales_amount": 2000,
                    "total_amount": 2000,
                }
            ],
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "This Square order ID is already in use."}


def test_missing_location_returns_not_found(client: TestClient) -> None:
    response = client.post(
        "/api/orders",
        json={
            "location_id": 999,
            "subtotal_amount": 1000,
            "total_amount": 1000,
            "line_items": [
                {
                    "item_name": "Tea",
                    "quantity": 1,
                    "unit_price_amount": 1000,
                    "gross_sales_amount": 1000,
                    "total_amount": 1000,
                }
            ],
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Location not found."}


def test_total_mismatch_fails_validation(client: TestClient) -> None:
    location_response = client.post(
        "/api/locations",
        json={"name": "West Ashley"},
    )
    location_id = location_response.json()["id"]

    response = client.post(
        "/api/orders",
        json={
            "location_id": location_id,
            "subtotal_amount": 1000,
            "discount_amount": 100,
            "tax_amount": 50,
            "service_charge_amount": 0,
            "total_amount": 900,
            "line_items": [
                {
                    "item_name": "Salad",
                    "quantity": 1,
                    "unit_price_amount": 1000,
                    "gross_sales_amount": 1000,
                    "discount_amount": 0,
                    "total_amount": 1000,
                }
            ],
        },
    )

    assert response.status_code == 422
    assert client.get("/api/orders").json() == []


def test_list_orders_returns_persisted_orders_with_line_items(
    client: TestClient,
) -> None:
    location_id = client.post(
        "/api/locations",
        json={"name": "Sushi 201"},
    ).json()["id"]

    created_order = client.post(
        "/api/orders",
        json={
            "location_id": location_id,
            "subtotal_amount": 1800,
            "tax_amount": 144,
            "total_amount": 1944,
            "line_items": [
                {
                    "item_name": "Spicy Tuna Roll",
                    "quantity": 1,
                    "unit_price_amount": 1400,
                    "gross_sales_amount": 1400,
                    "total_amount": 1400,
                },
                {
                    "item_name": "Edamame",
                    "quantity": 1,
                    "unit_price_amount": 400,
                    "gross_sales_amount": 400,
                    "total_amount": 400,
                },
            ],
        },
    )
    assert created_order.status_code == 201

    response = client.get("/api/orders")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == created_order.json()["id"]
    assert [item["item_name"] for item in response.json()[0]["line_items"]] == [
        "Spicy Tuna Roll",
        "Edamame",
    ]


def test_order_persists_across_request_sessions(client: TestClient) -> None:
    location_id = client.post(
        "/api/locations",
        json={"name": "Downtown"},
    ).json()["id"]
    create_response = client.post(
        "/api/orders",
        json={
            "location_id": location_id,
            "square_order_id": "PERSISTED-ORDER",
            "subtotal_amount": 600,
            "total_amount": 600,
            "line_items": [
                {
                    "item_name": "Soft Drink",
                    "quantity": 1,
                    "unit_price_amount": 600,
                    "gross_sales_amount": 600,
                    "total_amount": 600,
                }
            ],
        },
    )

    read_response = client.get(f"/api/orders/{create_response.json()['id']}")

    assert create_response.status_code == 201
    assert read_response.status_code == 200
    assert read_response.json()["square_order_id"] == "PERSISTED-ORDER"
    assert read_response.json()["line_items"][0]["item_name"] == "Soft Drink"


@pytest.mark.parametrize("quantity", [0, -1])
def test_nonpositive_quantity_is_rejected(
    client: TestClient,
    quantity: int,
) -> None:
    location_id = client.post(
        "/api/locations",
        json={"name": "West Ashley"},
    ).json()["id"]

    response = client.post(
        "/api/orders",
        json={
            "location_id": location_id,
            "subtotal_amount": 500,
            "total_amount": 500,
            "line_items": [
                {
                    "item_name": "Miso Soup",
                    "quantity": quantity,
                    "unit_price_amount": 500,
                    "gross_sales_amount": 500,
                    "total_amount": 500,
                }
            ],
        },
    )

    assert response.status_code == 422
    assert client.get("/api/orders").json() == []


@pytest.mark.parametrize(
    ("order_amounts", "line_amounts"),
    [
        ({"tax_amount": -1}, {}),
        ({}, {"unit_price_amount": -500}),
    ],
)
def test_negative_money_is_rejected(
    client: TestClient,
    order_amounts: dict[str, int],
    line_amounts: dict[str, int],
) -> None:
    location_id = client.post(
        "/api/locations",
        json={"name": "Mount Pleasant"},
    ).json()["id"]
    line_item = {
        "item_name": "Miso Soup",
        "quantity": 1,
        "unit_price_amount": 500,
        "gross_sales_amount": 500,
        "total_amount": 500,
        **line_amounts,
    }

    response = client.post(
        "/api/orders",
        json={
            "location_id": location_id,
            "subtotal_amount": 500,
            "total_amount": 500,
            **order_amounts,
            "line_items": [line_item],
        },
    )

    assert response.status_code == 422
    assert client.get("/api/orders").json() == []


def test_blank_item_name_is_rejected(client: TestClient) -> None:
    location_id = client.post(
        "/api/locations",
        json={"name": "James Island"},
    ).json()["id"]

    response = client.post(
        "/api/orders",
        json={
            "location_id": location_id,
            "subtotal_amount": 500,
            "total_amount": 500,
            "line_items": [
                {
                    "item_name": "   ",
                    "quantity": 1,
                    "unit_price_amount": 500,
                    "gross_sales_amount": 500,
                    "total_amount": 500,
                }
            ],
        },
    )

    assert response.status_code == 422
    assert client.get("/api/orders").json() == []


def test_demo_seed_is_idempotent(db_session: Session) -> None:
    first_seed = seed_demo_data(db_session)
    counts_after_first_seed = (
        db_session.scalar(select(func.count()).select_from(models.Location)),
        db_session.scalar(select(func.count()).select_from(models.Order)),
        db_session.scalar(select(func.count()).select_from(models.OrderLineItem)),
    )

    second_seed = seed_demo_data(db_session)
    counts_after_second_seed = (
        db_session.scalar(select(func.count()).select_from(models.Location)),
        db_session.scalar(select(func.count()).select_from(models.Order)),
        db_session.scalar(select(func.count()).select_from(models.OrderLineItem)),
    )

    assert first_seed == (4, 0)
    assert second_seed == (0, 4)
    assert counts_after_first_seed == counts_after_second_seed


def test_demo_seed_menu_totals_reconcile_and_existing_seed_refreshes(
    db_session: Session,
) -> None:
    seed_demo_data(db_session)
    order = db_session.scalar(
        select(models.Order).where(
            models.Order.square_order_id == "LEDGER201-DEMO-ORDER-001"
        )
    )
    payment = db_session.scalar(
        select(models.Payment).where(
            models.Payment.square_payment_id == "LEDGER201-DEMO-PAYMENT-001"
        )
    )
    assert order is not None
    assert payment is not None

    first_item = db_session.scalar(
        select(models.OrderLineItem)
        .where(models.OrderLineItem.order_id == order.id)
        .order_by(models.OrderLineItem.id)
    )
    assert first_item is not None
    first_item.item_name = "Old placeholder item"
    payment.amount = 1
    db_session.commit()

    seed_demo_data(db_session)
    demo_orders = list(
        db_session.scalars(
            select(models.Order)
            .where(models.Order.square_order_id.like("LEDGER201-DEMO-ORDER-%"))
            .order_by(models.Order.square_order_id)
        ).all()
    )
    expected_totals = {
        "LEDGER201-DEMO-ORDER-001": (1597, 0, 128, 1725),
        "LEDGER201-DEMO-ORDER-002": (4294, 300, 320, 4314),
        "LEDGER201-DEMO-ORDER-003": (5496, 500, 400, 5396),
        "LEDGER201-DEMO-ORDER-004": (6496, 0, 520, 7016),
    }

    assert len(demo_orders) == 4
    for demo_order in demo_orders:
        expected_subtotal, expected_discount, expected_tax, expected_total = (
            expected_totals[demo_order.square_order_id]
        )
        line_items = list(
            db_session.scalars(
                select(models.OrderLineItem)
                .where(models.OrderLineItem.order_id == demo_order.id)
                .order_by(models.OrderLineItem.id)
            ).all()
        )
        assert sum(item.gross_sales_amount for item in line_items) == expected_subtotal
        assert demo_order.subtotal_amount == expected_subtotal
        assert demo_order.discount_amount == expected_discount
        assert demo_order.tax_amount == expected_tax
        assert demo_order.total_amount == expected_total
        assert (
            demo_order.subtotal_amount
            - demo_order.discount_amount
            + demo_order.tax_amount
            + demo_order.service_charge_amount
            == demo_order.total_amount
        )
        completed_payment = db_session.scalar(
            select(models.Payment).where(
                models.Payment.order_id == demo_order.id,
                models.Payment.status == "COMPLETED",
            )
        )
        assert completed_payment is not None
        assert completed_payment.amount == demo_order.total_amount

    db_session.refresh(order)
    db_session.refresh(payment)
    first_order_items = list(
        db_session.scalars(
            select(models.OrderLineItem)
            .where(models.OrderLineItem.order_id == order.id)
            .order_by(models.OrderLineItem.id)
        ).all()
    )
    assert [item.item_name for item in first_order_items] == [
        "California",
        "Miso Soup",
        "Edamame",
    ]
    assert payment.amount == order.total_amount


def test_order_and_line_items_rollback_together_on_child_failure(
    db_session: Session,
) -> None:
    location = models.Location(name="Atomicity Test")
    db_session.add(location)
    db_session.commit()

    db_session.execute(
        text(
            "CREATE TRIGGER fail_order_line_item BEFORE INSERT "
            "ON order_line_items WHEN NEW.item_name = 'Edamame' BEGIN "
            "SELECT RAISE(ABORT, 'simulated line item insert failure'); "
            "END"
        )
    )
    db_session.commit()

    order_data = schemas.OrderCreate(
        location_id=location.id,
        square_order_id="ATOMIC-ORDER",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        subtotal_amount=1000,
        total_amount=1000,
        line_items=[
            schemas.OrderLineItemCreate(
                item_name="Miso Soup",
                quantity=1,
                unit_price_amount=500,
                gross_sales_amount=500,
                total_amount=500,
            ),
            schemas.OrderLineItemCreate(
                item_name="Edamame",
                quantity=1,
                unit_price_amount=500,
                gross_sales_amount=500,
                total_amount=500,
            ),
        ],
    )

    with pytest.raises(IntegrityError):
        create_order(db_session, order_data)

    assert db_session.scalar(select(func.count()).select_from(models.Order)) == 0
    assert (
        db_session.scalar(select(func.count()).select_from(models.OrderLineItem))
        == 0
    )


def test_invalid_child_request_leaves_no_order(client: TestClient) -> None:
    location_id = client.post(
        "/api/locations",
        json={"name": "Order Validation Child"},
    ).json()["id"]

    response = client.post(
        "/api/orders",
        json={
            "location_id": location_id,
            "subtotal_amount": 500,
            "total_amount": 500,
            "line_items": [
                {
                    "item_name": "Miso Soup",
                    "quantity": -1,
                    "unit_price_amount": 500,
                    "gross_sales_amount": 500,
                    "total_amount": 500,
                }
            ],
        },
    )

    assert response.status_code == 422
    assert client.get("/api/orders").json() == []


def test_invalid_order_request_leaves_no_order(client: TestClient) -> None:
    location_id = client.post(
        "/api/locations",
        json={"name": "Order Validation Total"},
    ).json()["id"]

    response = client.post(
        "/api/orders",
        json={
            "location_id": location_id,
            "subtotal_amount": 500,
            "tax_amount": 50,
            "total_amount": 500,
            "line_items": [
                {
                    "item_name": "Miso Soup",
                    "quantity": 1,
                    "unit_price_amount": 500,
                    "gross_sales_amount": 500,
                    "total_amount": 500,
                }
            ],
        },
    )

    assert response.status_code == 422
    assert client.get("/api/orders").json() == []
