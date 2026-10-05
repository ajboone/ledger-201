import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app import models
from app.services import monthly_analyst as analyst
from app.services.ai_analyst import _tool_result, _SYSTEM_INSTRUCTIONS, AIAnalystInvalidToolCallError
from app.services.square_category_classification import classify_category
from app.services.square_sales_report_import import import_square_sales_report
from app.services.square_sales_report_parser import parse_square_sales_report
from tests.test_square_sales_reports import REAL_SQUARE_EMAIL_REPORT
from tests.test_ai_analyst import _fake_client, _function_call, _response, _run


# Exact selected item and routing rows observed in the local September import.
# This is an excerpt, not a fabricated complete menu or a reconciled full report.
ITEMS = [
    ("Teriyaki Chicken", 158, 238640),
    ("Hibachi Steak", 86, 180614),
    ("Downtown roll", 202, 164668),
    ("Dynamite Roll", 157, 141243),
    ("California Roll", 135, 96905),
]
ROUTING = [("Kitchen Print", 1755, 2160890), ("Sushi Print", 1840, 1861272), ("Both Printers", 561, 707909)]
MENU = ["Beer", "Wine", "Coffee & Tea", "Salads & Soups", "Poke Bowls", "Yaki Soba & Yaki Udon"]


def report_text(items=None, categories=None):
    if items is None:
        items = "\n".join(f"{name} × {quantity} ${cents / 100:.2f}\nRegular × {quantity} ${cents / 100:.2f}" for name, quantity, cents in ITEMS)
    if categories is None:
        categories = "\n".join(f"{name} × {quantity} ${cents / 100:.2f}" for name, quantity, cents in ROUTING)
        categories += "\n" + "\n".join(f"{name} × 1 $10.00" for name in [*MENU, "Uncategorized", "Unmapped department"])
    return REAL_SQUARE_EMAIL_REPORT.split("Category Sales")[0] + "Category Sales\n" + categories + "\nItem Sales\n" + items


@pytest.fixture
def report(db_session):
    location = models.Location(name="Sushi 201")
    db_session.add(location)
    db_session.commit()
    return import_square_sales_report(db_session, location.id, report_text()).report


@pytest.mark.parametrize("layout", ["one-line", "vertical", "plain-quantity"])
def test_real_item_variations_normalized_across_layouts(layout):
    items = None
    if layout != "one-line":
        prefix = "× " if layout == "vertical" else ""
        items = "\n\n".join(f"{name}\n{prefix}{quantity}\n${cents / 100:.2f}\nRegular\n{prefix}{quantity}\n${cents / 100:.2f}" for name, quantity, cents in ITEMS)
    parsed = parse_square_sales_report(report_text(items))
    assert [(r.item_name, r.variation_name, r.quantity, r.sales_amount) for r in parsed.items] == [
        (name, "Regular", Decimal(quantity), cents) for name, quantity, cents in ITEMS
    ]


def test_non_regular_variation_and_ambiguous_equal_items():
    parsed = parse_square_sales_report(report_text("Soup\n2\n$10.00\n  Large\n2\n$10.00\nRoll A\n3\n$15.00\nRoll B\n3\n$15.00"))
    assert [(r.item_name, r.variation_name) for r in parsed.items] == [("Soup", "Large"), ("Roll A", None), ("Roll B", None)]
    assert any("lack variation evidence" in w for w in parsed.warnings)
    repeated = parse_square_sales_report(report_text().replace("Regular", "Dinner size"))
    assert all(r.variation_name == "Dinner size" for r in repeated.items)


def test_nonmatching_child_is_not_folded_or_ranked_without_warning():
    parsed = parse_square_sales_report(report_text("Soup\n2\n$10.00\n  Large\n1\n$6.00"))
    assert [(r.item_name, r.variation_name, r.sales_amount) for r in parsed.items] == [("Soup", None, 1000)]
    assert any("Unassociated variation" in note for note in parsed.warnings)


def test_parser_does_not_merge_across_an_intervening_label():
    parsed = parse_square_sales_report(report_text("Soup\n2\n$10.00\nUnparsed label\n  Large\n2\n$10.00"))
    assert [(r.item_name, r.variation_name) for r in parsed.items] == [("Soup", None), ("Large", None)]
    assert parsed.warnings


def test_legacy_stored_rows_normalized_without_database_mutation(db_session, report):
    report.item_sales.clear()
    db_session.flush()
    for name, quantity, cents in ITEMS:
        report.item_sales.extend([
            models.SquareItemSales(item_name=name + " ×", quantity=quantity, sales_amount=cents),
            models.SquareItemSales(item_name="Regular ×", quantity=quantity, sales_amount=cents),
        ])
    db_session.commit()
    for fn in [analyst.get_monthly_top_items, analyst.get_monthly_top_items_by_revenue, analyst.get_monthly_top_items_by_quantity]:
        result = fn(db_session, report.location_id, 2026, 9)
        assert len(result) == 5
        assert all(r.variation_name == "Regular" for r in result)
        assert all(r.item_name != "Regular" for r in result)
    concentration = analyst.get_monthly_sales_concentration(db_session, report.location_id, 2026, 9)
    assert concentration.top_n_sales == sum(cents for _, _, cents in ITEMS)
    assert len(list(db_session.scalars(select(models.SquareItemSales)))) == 10


def test_revenue_and_volume_rankings_and_decimal_unit_sales(db_session, report):
    revenue = analyst.get_monthly_top_items_by_revenue(db_session, report.location_id, 2026, 9)
    volume = analyst.get_monthly_top_items_by_quantity(db_session, report.location_id, 2026, 9)
    assert revenue[0].item_name == "Teriyaki Chicken"
    assert volume[0].item_name == "Downtown roll"
    assert [r.rank for r in revenue] == list(range(1, 6))
    assert revenue[0].reported_revenue_per_unit == Decimal("1510.3797")
    assert revenue[1].reported_revenue_per_unit == Decimal("2100.1628")
    assert all(r.data_quality_notes for r in revenue)  # excerpt does not equal full Items total


def test_ties_and_zero_quantity_are_deterministic(db_session, report):
    report.item_sales.clear()
    for name in ["Zulu", "alpha", "Alpha"]:
        report.item_sales.append(models.SquareItemSales(item_name=name, variation_name="Known", quantity=0, sales_amount=100))
    db_session.commit()
    for fn in [analyst.get_monthly_top_items_by_revenue, analyst.get_monthly_top_items_by_quantity]:
        result = fn(db_session, report.location_id, 2026, 9)
        assert [r.item_name for r in result] == ["Alpha", "alpha", "Zulu"]
        assert all(r.reported_revenue_per_unit is None for r in result)


def test_fractional_quantities_and_zero_routing_total(db_session, report):
    report.item_sales.clear()
    report.item_sales.append(models.SquareItemSales(item_name="Fractional", quantity=Decimal("0.125"), sales_amount=100))
    for row in report.category_sales:
        row.sales_amount = 0
    db_session.commit()
    metrics = analyst.get_monthly_item_sales_metrics(db_session, report.location_id, 2026, 9)
    assert metrics.items[0].reported_revenue_per_unit == Decimal("800.0000")
    routing = analyst.get_monthly_routing_mix(db_session, report.location_id, 2026, 9)
    assert all(row.revenue_share_percent is None for row in routing.categories)
    assert routing.data_quality_notes


def test_legacy_raw_category_labels_preserved_and_classified(db_session, report):
    for row in report.category_sales:
        row.category_name += " ×"
    db_session.commit()
    raw = analyst.get_monthly_category_performance(db_session, report.location_id, 2026, 9)
    assert raw[0].category_name == "Kitchen Print ×"
    assert raw[0].classification == "operational_routing"
    routing = analyst.get_monthly_routing_mix(db_session, report.location_id, 2026, 9)
    assert routing.categories[0].category_name == "Kitchen Print"
    assert routing.categories[0].raw_category_name == "Kitchen Print ×"


@pytest.mark.parametrize("bad_value", [0, -1, True, 1.5])
def test_invalid_limits_are_rejected(db_session, report, bad_value):
    for fn in [analyst.get_monthly_top_items_by_revenue, analyst.get_monthly_top_items_by_quantity, analyst.get_monthly_sales_concentration]:
        with pytest.raises(analyst.MonthlyAnalystValidationError):
            fn(db_session, report.location_id, 2026, 9, bad_value)


@pytest.mark.parametrize("label", MENU + ["Beverage", "Beverages & Extra Sauces", "Sushi Rolls", "Donburi & Katsu", "Appetizers"])
def test_menu_classification(label):
    assert classify_category(label) == "menu_category"
    assert classify_category(" " + label.upper() + " × ") == "menu_category"


def test_category_breakdown_and_routing_shares(db_session, report):
    breakdown = analyst.get_monthly_category_breakdown(db_session, report.location_id, 2026, 9)
    assert {r.category_name for r in breakdown.menu_categories} == set(MENU)
    assert {r.category_name for r in breakdown.routing_categories} == {r[0] for r in ROUTING}
    assert breakdown.uncategorized[0].category_name == "Uncategorized"
    assert breakdown.unknown[0].category_name == "Unmapped department"
    mix = analyst.get_monthly_routing_mix(db_session, report.location_id, 2026, 9)
    assert mix.total_routing_sales == 4730071
    assert [r.revenue_share_percent for r in mix.categories] == [Decimal("45.68"), Decimal("39.35"), Decimal("14.97")]
    assert all(r.classification == "operational_routing" for r in mix.categories)
    assert [(r.quantity, r.sales_amount) for r in mix.categories] == [(q, s) for _, q, s in ROUTING]


@pytest.mark.parametrize("top_n", [5, 10])
def test_concentration_uses_authoritative_denominator(db_session, report, top_n):
    result = analyst.get_monthly_sales_concentration(db_session, report.location_id, 2026, 9, top_n)
    assert result.top_n == top_n
    assert result.top_n_sales == 822070
    assert result.total_item_sales == 5355174
    assert result.revenue_share_percent == Decimal("15.35")


def test_top_five_and_ten_are_distinct_for_larger_menu(db_session, report):
    report.item_sales.clear()
    for index in range(1, 12):
        report.item_sales.append(models.SquareItemSales(item_name=f"Item {index}", quantity=index, sales_amount=index * 100))
    report.item_sales_amount = 6600
    db_session.commit()
    five = analyst.get_monthly_sales_concentration(db_session, report.location_id, 2026, 9, 5)
    ten = analyst.get_monthly_sales_concentration(db_session, report.location_id, 2026, 9, 10)
    assert five.top_n_sales == 4500
    assert ten.top_n_sales == 6500
    assert five.revenue_share_percent == Decimal("68.18")
    assert ten.revenue_share_percent == Decimal("98.48")


def test_empty_and_zero_denominators(db_session, report):
    report.item_sales_amount = 0
    report.category_sales.clear()
    db_session.commit()
    assert analyst.get_monthly_sales_concentration(db_session, report.location_id, 2026, 9).revenue_share_percent is None
    assert analyst.get_monthly_routing_mix(db_session, report.location_id, 2026, 9).categories == []
    report.item_sales.clear()
    report.item_sales_amount = 100
    db_session.commit()
    result = analyst.get_monthly_sales_concentration(db_session, report.location_id, 2026, 9)
    assert result.revenue_share_percent is None
    assert result.data_quality_notes


TOOLS = [
    ("get_monthly_top_items_by_revenue", "monthly-top-items-revenue", {"limit": 5}),
    ("get_monthly_top_items_by_quantity", "monthly-top-items-quantity", {"limit": 5}),
    ("get_monthly_item_sales_metrics", "monthly-item-sales-metrics", {}),
    ("get_monthly_category_breakdown", "monthly-category-breakdown", {}),
    ("get_monthly_routing_mix", "monthly-routing-mix", {}),
    ("get_monthly_sales_concentration", "monthly-sales-concentration", {"top_n": 5}),
]


@pytest.mark.parametrize("name,path,args", TOOLS)
def test_new_endpoints_and_ai_dispatch(client, db_session, report, name, path, args):
    arguments = {"year": 2026, "month": 9, **args}
    response = client.get(f"/api/analyst/{path}", params={"location_id": report.location_id, **arguments})
    assert response.status_code == 200
    output, normalized = _tool_result(db_session, report.location_id, name, json.dumps(arguments))
    assert output == response.json()
    assert normalized["location_id"] == report.location_id
    assert client.get(f"/api/analyst/{path}", params={"location_id": report.location_id, **arguments, "month": 13}).status_code == 422
    assert client.get(f"/api/analyst/{path}", params={"location_id": 999, **arguments}).status_code == 404
    assert client.get(f"/api/analyst/{path}", params={"location_id": report.location_id, **arguments, "month": 8}).status_code == 404
    with pytest.raises(AIAnalystInvalidToolCallError):
        _tool_result(db_session, report.location_id, name, json.dumps({**arguments, "location_id": 999}))


@pytest.mark.parametrize("name,path,args", TOOLS)
def test_ai_tool_loop_uses_new_metrics_without_live_calls(db_session, report, name, path, args):
    fake, responses = _fake_client(
        _response([_function_call(name, json.dumps({"year": 2026, "month": 9, **args}), "monthly")]),
        _response([SimpleNamespace(type="message")], "Analysis based on reported monthly facts."),
    )
    result = _run(db_session, fake, report.location_id, "Analyze September 2026.")
    assert result.tool_calls_used[0].tool == name
    output = json.loads(responses.calls[1]["input"][-1]["output"])
    assert output
    assert "Without cost data" in responses.calls[0]["instructions"]
    assert "operational production-routing" in _SYSTEM_INSTRUCTIONS
