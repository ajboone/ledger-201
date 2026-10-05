import json
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, select, text

from app import models
from app.demo.seed import seed_demo_data
from app.migrate_provenance import migrate
from app.services.ai_analyst import _tool_result
from app.services.daily_review import get_daily_review
from app.services.monthly_analyst import get_data_coverage
from app.square_sales_report_schemas import MonthlyDataCoverage
from tests.test_ai_analyst import _seed_monthly_report


def seed(db):
    seed_demo_data(db)
    return db.scalar(select(models.Location)).id


def test_seed_marks_demo_and_remains_idempotent(db_session):
    location_id = seed(db_session)
    ids = list(db_session.scalars(select(models.Order.id)))
    assert seed_demo_data(db_session) == (0, 4)
    assert list(db_session.scalars(select(models.Order.id))) == ids
    assert set(db_session.scalars(select(models.Order.provenance))) == {"demo"}
    review = get_daily_review(db_session, location_id, date(2026, 9, 14), provenances=("demo",))
    assert review.completed_refund_amount == 724
    assert review.reconciliation_difference == -724
    assert review.reconciliation_status == "REVIEW_REQUIRED"


@pytest.mark.parametrize("monthly,demo", [(False, False), (False, True), (True, False), (True, True)])
def test_coverage_combinations(db_session, monthly, demo):
    location = models.Location(name="Sushi 201")
    db_session.add(location)
    db_session.commit()
    if demo:
        seed_demo_data(db_session)
    if monthly:
        _seed_monthly_report(db_session, location.id)
    coverage = get_data_coverage(db_session, location.id)
    assert MonthlyDataCoverage.model_validate_json(coverage.model_dump_json()) == coverage
    assert coverage.has_real_transaction_data is False
    assert coverage.has_demo_transaction_data is demo
    assert coverage.demo_transaction_data_present is demo
    assert coverage.has_monthly_reports is monthly
    assert coverage.monthly_report_count == int(monthly)
    assert coverage.available_real_granularity == (["monthly_aggregate"] if monthly else [])
    assert coverage.available_demo_granularity == (["daily", "transaction"] if demo else [])
    assert coverage.latest_monthly_report_end == (date(2026, 9, 30) if monthly else None)


DAILY_CALLS = [
    ("get_daily_summary", {"review_date": "2026-09-14"}),
    ("get_top_items", {"review_date": "2026-09-14", "limit": 5}),
    ("get_refund_summary", {"review_date": "2026-09-14"}),
    ("get_discount_summary", {"review_date": "2026-09-14"}),
    ("get_reconciliation_exceptions", {"review_date": "2026-09-14"}),
    ("compare_daily_performance", {"date_a": "2026-09-14", "date_b": "2026-09-16"}),
]


@pytest.mark.parametrize("name,args", DAILY_CALLS)
def test_demo_only_tools_refuse(db_session, name, args):
    location_id = seed(db_session)
    output, _ = _tool_result(db_session, location_id, name, json.dumps(args))
    assert output["error"] == "transaction_level_data_unavailable"
    assert "5396" not in json.dumps(output)


@pytest.mark.parametrize("name,args", DAILY_CALLS)
def test_mixed_provenance_tools_exclude_demo(db_session, name, args):
    location_id = seed(db_session)
    db_session.add(models.Order(location_id=location_id, provenance="square_import", created_at=datetime(2026, 9, 14, 12), subtotal_amount=100, total_amount=100))
    db_session.commit()
    output, _ = _tool_result(db_session, location_id, name, json.dumps(args))
    serialized = json.dumps(output)
    assert "LEDGER201-DEMO" not in serialized
    assert "5396" not in serialized
    assert "724" not in serialized
    if name == "get_daily_summary":
        assert output["order_count"] == 1
        assert output["order_total_amount"] == 100
    if name == "get_top_items":
        assert output == []
    if name == "get_refund_summary":
        assert output["refunds"] == []


def test_unknown_ids_never_establish_provenance_and_locations_are_isolated(db_session):
    location_id = seed(db_session)
    other = models.Location(name="Other")
    db_session.add(other)
    db_session.flush()
    db_session.add(models.Order(location_id=other.id, provenance="square_import"))
    db_session.add(models.Order(location_id=location_id, square_order_id="demo-looking-arbitrary-id"))
    db_session.commit()
    coverage = get_data_coverage(db_session, location_id)
    assert coverage.has_unknown_transaction_data
    assert not coverage.has_real_transaction_data
    other_coverage = get_data_coverage(db_session, other.id)
    assert other_coverage.has_real_transaction_data
    assert not other_coverage.has_demo_transaction_data


def test_migration_is_idempotent_and_does_not_infer_existing_rows():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE orders (id INTEGER PRIMARY KEY, square_order_id TEXT)"))
        connection.execute(text("INSERT INTO orders VALUES (1, 'LEDGER201-DEMO-ORDER-001'), (2, 'real-looking')"))
    migrate(engine)
    migrate(engine)
    with engine.connect() as connection:
        assert list(connection.execute(text("SELECT provenance FROM orders")).scalars()) == ["unknown", "unknown"]
    engine.dispose()


def test_seed_backfills_only_reserved_fixture_ids(db_session):
    location_id = seed(db_session)
    for order in db_session.scalars(select(models.Order)):
        order.provenance = "unknown"
    arbitrary = models.Order(location_id=location_id, square_order_id="LEDGER201-DEMO-ORDER-999")
    db_session.add(arbitrary)
    db_session.commit()
    seed_demo_data(db_session)
    assert arbitrary.provenance == "unknown"
    assert len(list(db_session.scalars(select(models.Order).where(models.Order.provenance == "demo")))) == 4


def test_monthly_tool_uses_report_with_demo_present(db_session):
    location_id = seed(db_session)
    report = _seed_monthly_report(db_session, location_id)
    output, _ = _tool_result(db_session, location_id, "get_monthly_report_summary", '{"year":2026,"month":9}')
    assert output["report_id"] == report.id
    assert output["gross_sales_amount"] == report.gross_sales_amount


def test_coverage_and_demo_filter_api(client, db_session):
    location_id = seed(db_session)
    db_session.add(models.Order(location_id=location_id, provenance="manual", created_at=datetime(2026, 9, 14, 12), subtotal_amount=100, total_amount=100))
    db_session.commit()
    coverage = client.get("/api/analyst/coverage", params={"location_id": location_id})
    assert coverage.status_code == 200
    assert coverage.json()["has_real_transaction_data"] is True
    assert coverage.json()["has_demo_transaction_data"] is True
    response = client.get("/api/daily-review", params={"location_id": location_id, "date": "2026-09-14", "provenance": "demo"})
    assert response.status_code == 200
    assert response.json()["order_count"] == 1
    assert response.json()["order_total_amount"] == 5396
    assert response.json()["reconciliation_difference"] == -724


def test_seed_refuses_to_relabel_explicit_real_fixture(db_session):
    seed(db_session)
    order = db_session.scalar(select(models.Order).order_by(models.Order.id))
    order.provenance = "square_import"
    db_session.commit()
    with pytest.raises(RuntimeError, match="explicitly marked as real"):
        seed_demo_data(db_session)
    assert order.provenance == "square_import"
