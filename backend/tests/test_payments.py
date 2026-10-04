import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.demo.seed import seed_demo_data
from app.services.payments import create_payment, create_refund


def _create_order(client: TestClient, total_amount: int = 5000) -> int:
    location = client.post(
        "/api/locations",
        json={"name": "Sushi 201"},
    ).json()
    order_response = client.post(
        "/api/orders",
        json={
            "location_id": location["id"],
            "square_order_id": "PAYMENT-TEST-ORDER",
            "subtotal_amount": total_amount,
            "total_amount": total_amount,
            "line_items": [],
        },
    )
    assert order_response.status_code == 201
    return order_response.json()["id"]


def _create_order_model(db_session: Session, total_amount: int = 5000) -> models.Order:
    location = models.Location(name="Sushi 201")
    order = models.Order(
        location=location,
        state="COMPLETED",
        currency="USD",
        subtotal_amount=total_amount,
        discount_amount=0,
        tax_amount=0,
        service_charge_amount=0,
        total_amount=total_amount,
    )
    db_session.add(order)
    db_session.commit()
    return order


def _create_payment(
    client: TestClient,
    order_id: int,
    *,
    amount: int = 1000,
    square_payment_id: str = "PAYMENT-TEST-ID",
    payment_status: str = "COMPLETED",
) -> dict:
    response = client.post(
        "/api/payments",
        json={
            "order_id": order_id,
            "square_payment_id": square_payment_id,
            "status": payment_status,
            "source_type": "card",
            "currency": "usd",
            "amount": amount,
        },
    )
    assert response.status_code == 201
    return response.json()


def _refund_payload(
    payment_id: int,
    *,
    amount: int = 300,
    square_refund_id: str = "REFUND-TEST-ID",
    refund_status: str = "COMPLETED",
) -> dict:
    return {
        "payment_id": payment_id,
        "square_refund_id": square_refund_id,
        "status": refund_status,
        "currency": "USD",
        "amount": amount,
    }


def test_create_payment_associates_with_order(client: TestClient) -> None:
    order_id = _create_order(client)

    response = client.post(
        "/api/payments",
        json={
            "order_id": order_id,
            "square_payment_id": "SQ-PAYMENT-1",
            "status": "completed",
            "source_type": "card",
            "currency": "usd",
            "amount": 5000,
        },
    )

    assert response.status_code == 201
    payment = response.json()
    assert payment["order_id"] == order_id
    assert payment["square_payment_id"] == "SQ-PAYMENT-1"
    assert payment["status"] == "COMPLETED"
    assert payment["source_type"] == "CARD"
    assert payment["currency"] == "USD"
    assert payment["amount"] == 5000


def test_list_payments_and_filter_by_order(client: TestClient) -> None:
    order_id = _create_order(client)
    payment = _create_payment(client, order_id)

    response = client.get(f"/api/payments?order_id={order_id}")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [payment["id"]]


def test_duplicate_square_payment_id_returns_conflict(client: TestClient) -> None:
    order_id = _create_order(client)
    _create_payment(client, order_id)

    response = client.post(
        "/api/payments",
        json={
            "order_id": order_id,
            "square_payment_id": "PAYMENT-TEST-ID",
            "status": "COMPLETED",
            "currency": "USD",
            "amount": 1000,
        },
    )

    assert response.status_code == 409


def test_payment_for_missing_order_returns_not_found(client: TestClient) -> None:
    response = client.post(
        "/api/payments",
        json={
            "order_id": 999,
            "status": "COMPLETED",
            "currency": "USD",
            "amount": 1000,
        },
    )

    assert response.status_code == 404
    assert client.get("/api/payments").json() == []


@pytest.mark.parametrize("amount", [0, -1])
def test_nonpositive_payment_amount_is_rejected(
    client: TestClient,
    amount: int,
) -> None:
    order_id = _create_order(client)

    response = client.post(
        "/api/payments",
        json={
            "order_id": order_id,
            "status": "COMPLETED",
            "currency": "USD",
            "amount": amount,
        },
    )

    assert response.status_code == 422
    assert client.get("/api/payments").json() == []


def test_payment_persists_across_request_sessions(client: TestClient) -> None:
    order_id = _create_order(client)
    payment = _create_payment(client, order_id)

    response = client.get(f"/api/payments/{payment['id']}")

    assert response.status_code == 200
    assert response.json()["square_payment_id"] == "PAYMENT-TEST-ID"


def test_payment_currency_must_match_order(client: TestClient) -> None:
    order_id = _create_order(client)

    response = client.post(
        "/api/payments",
        json={
            "order_id": order_id,
            "status": "COMPLETED",
            "currency": "CAD",
            "amount": 1000,
        },
    )

    assert response.status_code == 422
    assert client.get("/api/payments").json() == []


def test_payment_currency_must_be_three_letters(client: TestClient) -> None:
    order_id = _create_order(client)
    response = client.post(
        "/api/payments",
        json={
            "order_id": order_id,
            "status": "COMPLETED",
            "currency": "US",
            "amount": 1000,
        },
    )

    assert response.status_code == 422


def test_failed_payment_insert_leaves_no_partial_record(
    db_session: Session,
) -> None:
    order = _create_order_model(db_session)
    db_session.execute(
        text(
            "CREATE TRIGGER fail_payment_insert BEFORE INSERT ON payments "
            "BEGIN SELECT RAISE(ABORT, 'simulated payment failure'); END"
        )
    )
    db_session.commit()

    payment_data = schemas.PaymentCreate(
        order_id=order.id,
        square_payment_id="ATOMIC-PAYMENT",
        status="COMPLETED",
        currency="USD",
        amount=1000,
    )

    with pytest.raises(IntegrityError):
        create_payment(db_session, payment_data)

    assert db_session.scalar(select(func.count()).select_from(models.Payment)) == 0


def test_create_refund_associates_with_payment(client: TestClient) -> None:
    order_id = _create_order(client)
    payment = _create_payment(client, order_id)

    response = client.post(
        "/api/refunds",
        json={
            **_refund_payload(payment["id"]),
            "reason": "Incorrect item",
        },
    )

    assert response.status_code == 201
    refund = response.json()
    assert refund["payment_id"] == payment["id"]
    assert refund["payment"]["id"] == payment["id"]
    assert refund["payment"]["order_id"] == order_id
    assert refund["payment"]["amount"] == 1000
    assert refund["square_refund_id"] == "REFUND-TEST-ID"
    assert refund["amount"] == 300
    assert refund["reason"] == "Incorrect item"


def test_list_refunds_and_filter_by_payment(client: TestClient) -> None:
    order_id = _create_order(client)
    payment = _create_payment(client, order_id)
    refund_response = client.post(
        "/api/refunds",
        json=_refund_payload(payment["id"]),
    )

    response = client.get(f"/api/refunds?payment_id={payment['id']}")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        refund_response.json()["id"]
    ]
    assert response.json()[0]["payment"]["id"] == payment["id"]


def test_duplicate_square_refund_id_returns_conflict(client: TestClient) -> None:
    order_id = _create_order(client)
    payment = _create_payment(client, order_id)
    client.post("/api/refunds", json=_refund_payload(payment["id"]))

    response = client.post(
        "/api/refunds",
        json=_refund_payload(
            payment["id"],
            square_refund_id="REFUND-TEST-ID",
            amount=200,
        ),
    )

    assert response.status_code == 409


def test_refund_for_missing_payment_returns_not_found(client: TestClient) -> None:
    response = client.post(
        "/api/refunds",
        json=_refund_payload(999),
    )

    assert response.status_code == 404
    assert client.get("/api/refunds").json() == []


@pytest.mark.parametrize("amount", [0, -1])
def test_nonpositive_refund_amount_is_rejected(
    client: TestClient,
    amount: int,
) -> None:
    order_id = _create_order(client)
    payment = _create_payment(client, order_id)

    response = client.post(
        "/api/refunds",
        json=_refund_payload(payment["id"], amount=amount),
    )

    assert response.status_code == 422
    assert client.get("/api/refunds").json() == []


def test_refund_cannot_exceed_payment_amount(client: TestClient) -> None:
    order_id = _create_order(client)
    payment = _create_payment(client, order_id, amount=1000)

    response = client.post(
        "/api/refunds",
        json=_refund_payload(payment["id"], amount=1001),
    )

    assert response.status_code == 409
    assert client.get("/api/refunds").json() == []


def test_cumulative_completed_and_pending_refunds_are_capped(
    client: TestClient,
) -> None:
    order_id = _create_order(client)
    payment = _create_payment(client, order_id, amount=1000)
    first_refund = client.post(
        "/api/refunds",
        json=_refund_payload(payment["id"], amount=600),
    )
    pending_refund = client.post(
        "/api/refunds",
        json=_refund_payload(
            payment["id"],
            amount=300,
            square_refund_id="REFUND-PENDING",
            refund_status="PENDING",
        ),
    )

    response = client.post(
        "/api/refunds",
        json=_refund_payload(
            payment["id"],
            amount=101,
            square_refund_id="REFUND-OVER-LIMIT",
        ),
    )

    assert first_refund.status_code == 201
    assert pending_refund.status_code == 201
    assert response.status_code == 409
    assert len(client.get("/api/refunds").json()) == 2


def test_pending_refunds_reserve_amount_but_failed_refunds_do_not(
    client: TestClient,
) -> None:
    order_id = _create_order(client)
    payment = _create_payment(client, order_id, amount=1000)
    pending = client.post(
        "/api/refunds",
        json=_refund_payload(
            payment["id"],
            amount=800,
            square_refund_id="REFUND-PENDING",
            refund_status="PENDING",
        ),
    )
    failed = client.post(
        "/api/refunds",
        json=_refund_payload(
            payment["id"],
            amount=900,
            square_refund_id="REFUND-FAILED",
            refund_status="FAILED",
        ),
    )
    completed = client.post(
        "/api/refunds",
        json=_refund_payload(
            payment["id"],
            amount=200,
            square_refund_id="REFUND-COMPLETED",
            refund_status="COMPLETED",
        ),
    )

    assert pending.status_code == 201
    assert failed.status_code == 201
    assert completed.status_code == 201
    assert {refund["status"] for refund in client.get("/api/refunds").json()} == {
        "PENDING",
        "FAILED",
        "COMPLETED",
    }


def test_refund_cannot_be_created_for_noncompleted_payment(
    client: TestClient,
) -> None:
    order_id = _create_order(client)
    payment = _create_payment(
        client,
        order_id,
        payment_status="PENDING",
    )

    response = client.post(
        "/api/refunds",
        json=_refund_payload(payment["id"]),
    )

    assert response.status_code == 409


def test_refund_currency_must_match_payment(client: TestClient) -> None:
    order_id = _create_order(client)
    payment = _create_payment(client, order_id)
    payload = _refund_payload(payment["id"])
    payload["currency"] = "CAD"

    response = client.post("/api/refunds", json=payload)

    assert response.status_code == 422
    assert client.get("/api/refunds").json() == []


def test_refund_currency_must_be_three_letters(client: TestClient) -> None:
    order_id = _create_order(client)
    payment = _create_payment(client, order_id)
    payload = _refund_payload(payment["id"])
    payload["currency"] = "US"

    response = client.post("/api/refunds", json=payload)

    assert response.status_code == 422


def test_failed_refund_insert_leaves_no_partial_record(
    db_session: Session,
) -> None:
    order = _create_order_model(db_session)
    payment = models.Payment(
        order=order,
        status="COMPLETED",
        currency="USD",
        amount=1000,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.execute(
        text(
            "CREATE TRIGGER fail_refund_insert BEFORE INSERT ON refunds "
            "BEGIN SELECT RAISE(ABORT, 'simulated refund failure'); END"
        )
    )
    db_session.commit()

    refund_data = schemas.RefundCreate(
        payment_id=payment.id,
        square_refund_id="ATOMIC-REFUND",
        status="COMPLETED",
        currency="USD",
        amount=300,
    )

    with pytest.raises(IntegrityError):
        create_refund(db_session, refund_data)

    assert db_session.scalar(select(func.count()).select_from(models.Refund)) == 0


def test_demo_seed_creates_payments_refunds_and_is_idempotent(
    db_session: Session,
) -> None:
    seed_demo_data(db_session)
    first_counts = (
        db_session.scalar(select(func.count()).select_from(models.Payment)),
        db_session.scalar(select(func.count()).select_from(models.Refund)),
    )

    seed_demo_data(db_session)
    second_counts = (
        db_session.scalar(select(func.count()).select_from(models.Payment)),
        db_session.scalar(select(func.count()).select_from(models.Refund)),
    )

    assert first_counts == (5, 3)
    assert second_counts == first_counts


def test_deleting_order_cascades_to_payments_and_refunds(
    db_session: Session,
) -> None:
    order = _create_order_model(db_session)
    payment = models.Payment(
        order=order,
        status="COMPLETED",
        currency="USD",
        amount=1000,
    )
    payment.refunds.append(
        models.Refund(
            square_refund_id="CASCADE-REFUND",
            status="COMPLETED",
            currency="USD",
            amount=300,
        )
    )
    db_session.add(payment)
    db_session.commit()

    db_session.delete(order)
    db_session.commit()

    assert db_session.scalar(select(func.count()).select_from(models.Payment)) == 0
    assert db_session.scalar(select(func.count()).select_from(models.Refund)) == 0
