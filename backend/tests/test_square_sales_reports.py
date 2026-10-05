from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.services.square_sales_report_import import (
    DuplicateSquareSalesReportError,
    get_square_sales_report,
    import_square_sales_report,
)
from app.services.square_sales_report_parser import (
    SquareSalesReportParseError,
    parse_currency_to_cents,
    parse_square_sales_report,
)


SQUARE_REPORT_TEXT = """Sushi 201
Sep 1, 2026 - Sep 30, 2026
Reported at: 2026-10-01T08:30:00-04:00

Sales
Gross Sales $12,345.67
Items $12,345.67
Service Charges $250.00
Returns ($12.34)
Discounts & Comps ($345.67)
Net Sales $12,237.66
Tax $1,234.56
Tips $987.65
Gift Card Sales $100.00
Refunds by Amount ($50.00)
Total $14,509.87

Payments
Total Collected $14,509.87
Fees ($321.00)
Net Total $14,188.87

Discounts Applied
Discount Name    Usage Count    Amount
Lunch Special    3    ($15.00)
Loyalty Reward    2    ($10.00)

Category Sales
Category    Quantity    Sales
Rolls    12.5    $345.67
Appetizers    9    $123.45

Item Sales
Item    Variation    Quantity    Sales
Spicy Tuna Roll    Regular    2.5    $42.50
Miso Soup    Cup    3    $15.00
"""

REAL_SQUARE_EMAIL_REPORT = """Sales Report

Sushi 201

Reported on Oct 04, 2026 4:54 PM EDT

Sep 01, 2026 12:00 AM - Sep 30, 2026 11:59 PM

All Employees

All Devices

Sales

Covers

0

Gross Sales

$54,013.32

Items

$53,551.74

Service Charges

$461.58

Returns

($131.65)

Discounts & Comps

($663.35)

Net Sales

$53,218.32

Tax

$5,791.95

Tips

$7,156.34

Gift Card Sales

$0.00

Refunds by Amount

($3.50)

Total

$66,163.11

Payments

Total Collected

$66,163.11

Fees

($1,361.00)

Net Total

$64,802.11

Discounts Applied

Employee discount

× 1

($7.50)

military

× 138

($655.85)

Category Sales

Appetizers

× 1

$3.49

Beer

× 97

$511.00

Beverage

× 26

$156.00

Item Sales

1 Pork Bun

× 35

$139.65

Regular

× 35

$139.65

Aburi Salmon

× 20

$130.00

Regular

× 20

$130.00

Decimal Quantity Item

× 348.0

$100.00

Four Decimal Quantity Item

× 561.0000

$200.00
"""


def _create_location(client: TestClient, name: str = "Sushi 201") -> int:
    response = client.post("/api/locations", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _import_report(client: TestClient, location_id: int, text: str = SQUARE_REPORT_TEXT):
    return client.post(
        "/api/square-reports/import",
        json={
            "location_id": location_id,
            "raw_report_text": text,
        },
    )


def test_parse_full_square_report_and_core_metrics() -> None:
    parsed = parse_square_sales_report(SQUARE_REPORT_TEXT)

    assert parsed.report_name == "Sushi 201"
    assert parsed.report_start.isoformat() == "2026-09-01"
    assert parsed.report_end.isoformat() == "2026-09-30"
    assert parsed.reported_at is not None
    assert parsed.gross_sales_amount == 1_234_567
    assert parsed.item_sales_amount == 1_234_567
    assert parsed.service_charge_amount == 25_000
    assert parsed.returns_amount == -1_234
    assert parsed.discount_comp_amount == -34_567
    assert parsed.net_sales_amount == 1_223_766
    assert parsed.tax_amount == 123_456
    assert parsed.tips_amount == 98_765
    assert parsed.gift_card_sales_amount == 10_000
    assert parsed.refund_amount == -5_000
    assert parsed.total_amount == 1_450_987
    assert parsed.total_collected_amount == 1_450_987
    assert parsed.fees_amount == -32_100
    assert parsed.net_total_amount == 1_418_887
    assert len(parsed.discounts) == 2
    assert len(parsed.categories) == 2
    assert len(parsed.items) == 2


def test_parse_parentheses_and_negative_currency_values() -> None:
    assert parse_currency_to_cents("($1,234.56)") == -123_456
    assert parse_currency_to_cents("-$12.30") == -1_230
    assert parse_currency_to_cents("$12.30") == 1_230


def test_parse_decimal_quantities_and_variation() -> None:
    parsed = parse_square_sales_report(SQUARE_REPORT_TEXT)

    assert parsed.categories[0].quantity == Decimal("12.5")
    assert parsed.items[0].quantity == Decimal("2.5")
    assert parsed.items[0].item_name == "Spicy Tuna Roll"
    assert parsed.items[0].variation_name == "Regular"


def test_parser_keeps_double_spaces_in_item_name_without_variation_column() -> None:
    no_variation = SQUARE_REPORT_TEXT.replace(
        "Item    Variation    Quantity    Sales",
        "Item    Quantity    Sales",
    ).replace(
        "Spicy Tuna Roll    Regular    2.5    $42.50",
        "Spicy  Tuna Roll    2.5    $42.50",
    )

    parsed = parse_square_sales_report(no_variation)

    assert parsed.items[0].item_name == "Spicy  Tuna Roll"
    assert parsed.items[0].variation_name is None


def test_parse_discount_category_and_item_sections() -> None:
    parsed = parse_square_sales_report(SQUARE_REPORT_TEXT)

    assert (parsed.discounts[0].discount_name, parsed.discounts[0].usage_count,
            parsed.discounts[0].amount) == ("Lunch Special", 3, -1_500)
    assert (parsed.categories[1].category_name, parsed.categories[1].quantity,
            parsed.categories[1].sales_amount) == (
        "Appetizers",
        Decimal("9"),
        12_345,
    )
    assert (parsed.items[1].item_name, parsed.items[1].variation_name,
            parsed.items[1].sales_amount) == ("Miso Soup", "Cup", 1_500)


def test_parser_tolerates_blank_lines() -> None:
    parsed = parse_square_sales_report(
        "\n\n" + SQUARE_REPORT_TEXT.replace("Payments\n", "\nPayments\n\n")
    )

    assert parsed.report_start.isoformat() == "2026-09-01"


def test_parse_real_square_email_report_and_financial_metrics() -> None:
    parsed = parse_square_sales_report(REAL_SQUARE_EMAIL_REPORT)

    assert parsed.report_name == "Sushi 201"
    assert parsed.report_start.isoformat() == "2026-09-01"
    assert parsed.report_end.isoformat() == "2026-09-30"
    assert parsed.reported_at is not None
    assert parsed.reported_at.isoformat() == "2026-10-04T16:54:00-04:00"
    assert parsed.gross_sales_amount == 5_401_332
    assert parsed.item_sales_amount == 5_355_174
    assert parsed.service_charge_amount == 46_158
    assert parsed.returns_amount == -13_165
    assert parsed.discount_comp_amount == -66_335
    assert parsed.net_sales_amount == 5_321_832
    assert parsed.tax_amount == 579_195
    assert parsed.tips_amount == 715_634
    assert parsed.gift_card_sales_amount == 0
    assert parsed.refund_amount == -350
    assert parsed.total_amount == 6_616_311
    assert parsed.total_collected_amount == 6_616_311
    assert parsed.fees_amount == -136_100
    assert parsed.net_total_amount == 6_480_211


def test_parse_real_email_discount_category_and_variation_rows() -> None:
    parsed = parse_square_sales_report(REAL_SQUARE_EMAIL_REPORT)

    assert [
        (row.discount_name, row.usage_count, row.amount)
        for row in parsed.discounts
    ] == [
        ("Employee discount", 1, -750),
        ("military", 138, -65_585),
    ]
    assert [
        (row.category_name, row.quantity, row.sales_amount)
        for row in parsed.categories
    ] == [
        ("Appetizers", Decimal("1"), 349),
        ("Beer", Decimal("97"), 51_100),
        ("Beverage", Decimal("26"), 15_600),
    ]
    assert [
        (row.item_name, row.variation_name, row.quantity, row.sales_amount)
        for row in parsed.items
    ] == [
        ("1 Pork Bun", "Regular", Decimal("35"), 13_965),
        ("Aburi Salmon", "Regular", Decimal("20"), 13_000),
        ("Decimal Quantity Item", None, Decimal("348.0"), 10_000),
        ("Four Decimal Quantity Item", None, Decimal("561.0000"), 20_000),
    ]


def test_variation_rows_are_not_counted_as_independent_item_sales() -> None:
    parsed = parse_square_sales_report(REAL_SQUARE_EMAIL_REPORT)
    pork_bun_rows = [row for row in parsed.items if row.item_name == "1 Pork Bun"]

    assert len(pork_bun_rows) == 1
    assert sum(row.sales_amount for row in pork_bun_rows) == 13_965


def test_parse_real_email_report_can_be_persisted_and_retrieved(
    db_session: Session,
) -> None:
    location = models.Location(name="Sushi 201")
    db_session.add(location)
    db_session.flush()

    outcome = import_square_sales_report(
        db_session,
        location.id,
        REAL_SQUARE_EMAIL_REPORT,
    )
    retrieved = get_square_sales_report(db_session, outcome.report.id)

    assert retrieved is not None
    assert retrieved.gross_sales_amount == 5_401_332
    assert len(retrieved.category_sales) == 3
    assert len(retrieved.item_sales) == 4
    assert len(retrieved.discount_summaries) == 2
    assert retrieved.item_sales[0].item_name == "1 Pork Bun"
    assert retrieved.item_sales[0].variation_name == "Regular"


def test_parser_warns_on_unreconciled_totals_without_rejecting_report() -> None:
    inconsistent = SQUARE_REPORT_TEXT.replace(
        "Net Sales $12,237.66",
        "Net Sales $11,000.00",
    )

    parsed = parse_square_sales_report(inconsistent)

    assert parsed.net_sales_amount == 1_100_000
    assert any("Net sales does not equal" in warning for warning in parsed.warnings)


def test_parser_rejects_malformed_currency() -> None:
    malformed = SQUARE_REPORT_TEXT.replace(
        "Gross Sales $12,345.67",
        "Gross Sales $12,34.56",
    )

    with pytest.raises(SquareSalesReportParseError, match="Invalid currency"):
        parse_square_sales_report(malformed)


def test_parser_rejects_missing_required_metric() -> None:
    incomplete = SQUARE_REPORT_TEXT.replace("Tips $987.65\n", "")

    with pytest.raises(SquareSalesReportParseError, match="tips_amount"):
        parse_square_sales_report(incomplete)


def test_parser_rejects_invalid_date_range() -> None:
    invalid_period = SQUARE_REPORT_TEXT.replace(
        "Sep 1, 2026 - Sep 30, 2026",
        "Sep 30, 2026 - Sep 1, 2026",
    )

    with pytest.raises(SquareSalesReportParseError, match="before"):
        parse_square_sales_report(invalid_period)


def test_parser_does_not_silently_skip_malformed_section_rows() -> None:
    malformed = SQUARE_REPORT_TEXT.replace(
        "Rolls    12.5    $345.67",
        "Rolls    12.5    $3x5.67",
    )

    with pytest.raises(SquareSalesReportParseError, match="malformed categories row"):
        parse_square_sales_report(malformed)


def test_import_persists_aggregate_children_without_transactions(
    client: TestClient,
) -> None:
    location_id = _create_location(client)

    response = _import_report(client, location_id)

    assert response.status_code == 201
    result = response.json()
    assert result["categories_imported"] == 2
    assert result["items_imported"] == 2
    assert result["discounts_imported"] == 2
    assert client.get("/api/orders").json() == []
    assert client.get("/api/payments").json() == []


def test_duplicate_report_period_returns_conflict(client: TestClient) -> None:
    location_id = _create_location(client)

    first_response = _import_report(client, location_id)
    second_response = _import_report(client, location_id)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert "already exists" in second_response.json()["detail"]
    assert len(client.get("/api/square-reports").json()) == 1


def test_import_rejects_nonexistent_location(client: TestClient) -> None:
    response = _import_report(client, 999)

    assert response.status_code == 404
    assert response.json() == {"detail": "Location not found."}


def test_failed_commit_rolls_back_report_and_all_children(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location = models.Location(name="Sushi 201")
    db_session.add(location)
    db_session.flush()

    def fail_commit() -> None:
        raise RuntimeError("simulated persistence failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="simulated persistence failure"):
        import_square_sales_report(db_session, location.id, SQUARE_REPORT_TEXT)

    assert db_session.scalar(select(func.count()).select_from(models.SquareSalesReport)) == 0
    assert db_session.scalar(select(func.count()).select_from(models.SquareCategorySales)) == 0
    assert db_session.scalar(select(func.count()).select_from(models.SquareItemSales)) == 0
    assert db_session.scalar(select(func.count()).select_from(models.SquareDiscountSummary)) == 0


def test_report_detail_returns_summary_and_all_child_rows(client: TestClient) -> None:
    location_id = _create_location(client)
    imported = _import_report(client, location_id).json()

    response = client.get(f"/api/square-reports/{imported['report_id']}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["location_id"] == location_id
    assert detail["gross_sales_amount"] == 1_234_567
    assert len(detail["category_sales"]) == 2
    assert len(detail["item_sales"]) == 2
    assert len(detail["discount_summaries"]) == 2
    assert detail["item_sales"][0]["variation_name"] == "Regular"


def test_report_list_and_location_filter(client: TestClient) -> None:
    sushi_location_id = _create_location(client)
    other_location_id = _create_location(client, "Downtown")
    _import_report(client, sushi_location_id)
    _import_report(client, other_location_id)

    all_reports = client.get("/api/square-reports")
    filtered_reports = client.get(
        "/api/square-reports",
        params={"location_id": sushi_location_id},
    )

    assert all_reports.status_code == 200
    assert len(all_reports.json()) == 2
    assert len(filtered_reports.json()) == 1
    assert filtered_reports.json()[0]["location_id"] == sushi_location_id


def test_missing_report_detail_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/square-reports/12345")

    assert response.status_code == 404


def test_import_parse_errors_return_validation_error(client: TestClient) -> None:
    location_id = _create_location(client)
    response = _import_report(client, location_id, "Not a Square report.")

    assert response.status_code == 422
    assert "date range" in response.json()["detail"]


def test_service_raises_duplicate_domain_error(db_session: Session) -> None:
    location = models.Location(name="Sushi 201")
    db_session.add(location)
    db_session.flush()

    import_square_sales_report(db_session, location.id, SQUARE_REPORT_TEXT)
    with pytest.raises(DuplicateSquareSalesReportError):
        import_square_sales_report(db_session, location.id, SQUARE_REPORT_TEXT)


def test_report_deletion_cascades_to_owned_aggregate_rows(
    db_session: Session,
) -> None:
    location = models.Location(name="Sushi 201")
    db_session.add(location)
    db_session.flush()
    outcome = import_square_sales_report(
        db_session,
        location.id,
        SQUARE_REPORT_TEXT,
    )

    db_session.delete(outcome.report)
    db_session.commit()

    assert db_session.scalar(select(func.count()).select_from(models.SquareCategorySales)) == 0
    assert db_session.scalar(select(func.count()).select_from(models.SquareItemSales)) == 0
    assert db_session.scalar(select(func.count()).select_from(models.SquareDiscountSummary)) == 0
