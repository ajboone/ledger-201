from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.provenance import REAL_PROVENANCE
from app.services.daily_review import LocationNotFoundError
from app.services.square_category_classification import classify_category
from app.services.square_item_normalization import ItemRow, normalize_items
from app.services.square_report_labels import clean_report_label
from app.square_sales_report_schemas import (
    LatestSquareReport,
    MonthlyCategoryPerformance,
    MonthlyDataCoverage,
    MonthlyDiscountDetail,
    MonthlyDiscountSummary,
    MonthlyReportComparison,
    MonthlyReportSummary,
    MonthlyTopItem,
    MonthlyItemSalesMetrics,
    MonthlySalesConcentration,
    MonthlyCategoryBreakdown,
    MonthlyRoutingCategory,
    MonthlyRoutingMix,
)


class MonthlyAnalystValidationError(ValueError):
    """Raised when a monthly report request contains invalid inputs."""


class MonthlyReportNotFoundError(MonthlyAnalystValidationError):
    """Raised when no monthly Square report exists for the requested period."""


def _validate_month_value(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MonthlyAnalystValidationError(f"{name} must be an integer.")
    return value


def _validate_year_and_month(year: int, month: int) -> tuple[int, int]:
    year = _validate_month_value("year", year)
    month = _validate_month_value("month", month)
    if year < 1970:
        raise MonthlyAnalystValidationError("year must be 1970 or later.")
    if month < 1 or month > 12:
        raise MonthlyAnalystValidationError("month must be between 1 and 12.")
    return year, month


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    year, month = _validate_year_and_month(year, month)
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    return start, end


def _location_or_raise(db: Session, location_id: int) -> models.Location:
    location = db.get(models.Location, location_id)
    if location is None:
        raise LocationNotFoundError("Location not found.")
    return location


def _report_for_month(
    db: Session,
    location_id: int,
    year: int,
    month: int,
) -> models.SquareSalesReport | None:
    start, end = _month_bounds(year, month)
    report = db.scalar(
        select(models.SquareSalesReport)
        .where(
            models.SquareSalesReport.location_id == location_id,
            models.SquareSalesReport.report_start <= end,
            models.SquareSalesReport.report_end >= start,
        )
        .order_by(
            models.SquareSalesReport.report_start.desc(),
            models.SquareSalesReport.id.desc(),
        )
    )
    return report


def _float_quantity(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    return float(value)


def _safe_percentage_change(base: int | None, value: int | None) -> float | None:
    if base in (None, 0):
        return None
    if value is None:
        return None
    return round((value - base) * 100 / base, 2)


def get_monthly_report_summary(
    db: Session,
    location_id: int,
    year: int,
    month: int,
) -> MonthlyReportSummary:
    """Return the authoritative monthly Square sales report summary for one month."""

    _location_or_raise(db, location_id)
    report = _report_for_month(db, location_id, year, month)
    if report is None:
        raise MonthlyReportNotFoundError(
            f"No Square monthly report was found for {year}-{month:02d}."
        )

    return MonthlyReportSummary(
        location_id=location_id,
        report_id=report.id,
        report_start=report.report_start,
        report_end=report.report_end,
        gross_sales_amount=report.gross_sales_amount,
        item_sales_amount=report.item_sales_amount,
        service_charge_amount=report.service_charge_amount,
        returns_amount=report.returns_amount,
        discount_comp_amount=report.discount_comp_amount,
        net_sales_amount=report.net_sales_amount,
        tax_amount=report.tax_amount,
        tips_amount=report.tips_amount,
        gift_card_sales_amount=report.gift_card_sales_amount,
        refund_amount=report.refund_amount,
        total_amount=report.total_amount,
        total_collected_amount=report.total_collected_amount,
        fees_amount=report.fees_amount,
        net_total_amount=report.net_total_amount,
        currency=report.location.currency,
        imported_at=report.created_at,
        created_at=report.created_at,
    )


def get_monthly_top_items(
    db: Session,
    location_id: int,
    year: int,
    month: int,
    limit: int = 10,
) -> list[MonthlyTopItem]:
    """Return the highest-value monthly items in deterministic order."""

    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise MonthlyAnalystValidationError("limit must be a positive integer.")

    report = _report_for_month(db, location_id, year, month)
    if report is None:
        raise MonthlyReportNotFoundError(
            f"No Square monthly report was found for {year}-{month:02d}."
        )

    return _rank_items(report, "revenue", limit)


def _analysis_report(db: Session, location_id: int, year: int, month: int):
    _location_or_raise(db, location_id)
    report = _report_for_month(db, location_id, year, month)
    if report is None:
        raise MonthlyReportNotFoundError(f"No Square monthly report was found for {year}-{month:02d}.")
    return report


def _context(report):
    return dict(report_id=report.id, report_start=report.report_start,
                report_end=report.report_end, currency=report.location.currency)


def _normalized_report_items(report):
    rows, notes = normalize_items([
        ItemRow(row.item_name, row.variation_name, Decimal(str(row.quantity)), row.sales_amount)
        for row in sorted(report.item_sales, key=lambda row: row.id)
    ])
    if not rows:
        notes.append("No usable item detail was reported; a ranking cannot be established.")
    if sum(row.sales_amount for row in rows) != report.item_sales_amount:
        notes.append("Normalized item detail does not reconcile to the report's Items total; rankings cover reported detail only and concentration may be incomplete.")
    return rows, notes


def _rank_items(report, sort_by: str, limit: int | None = None):
    rows, notes = _normalized_report_items(report)
    def key(row):
        metrics = (-row.sales_amount, -row.quantity) if sort_by == "revenue" else (-row.quantity, -row.sales_amount)
        return (*metrics, row.item_name.casefold(), (row.variation_name or "").casefold(), row.item_name, row.variation_name or "")
    return [MonthlyTopItem(
        item_name=row.item_name, variation_name=row.variation_name,
        quantity=float(row.quantity), sales_amount=row.sales_amount, rank=rank,
        reported_revenue_per_unit=(
            (Decimal(row.sales_amount) / row.quantity).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            if row.quantity else None
        ),
        data_quality_notes=notes,
    ) for rank, row in enumerate(sorted(rows, key=key)[:limit], start=1)]


def _positive_integer(value: int, name: str):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise MonthlyAnalystValidationError(f"{name} must be a positive integer.")


def get_monthly_top_items_by_revenue(db: Session, location_id: int, year: int, month: int, limit: int = 10):
    """Rank reported item/variation rows by revenue, then quantity, then name."""
    _positive_integer(limit, "limit")
    return _rank_items(_analysis_report(db, location_id, year, month), "revenue", limit)


def get_monthly_top_items_by_quantity(db: Session, location_id: int, year: int, month: int, limit: int = 10):
    """Rank reported item/variation rows by quantity, then revenue, then name."""
    _positive_integer(limit, "limit")
    return _rank_items(_analysis_report(db, location_id, year, month), "quantity", limit)


def get_monthly_item_sales_metrics(db: Session, location_id: int, year: int, month: int):
    report = _analysis_report(db, location_id, year, month)
    items = _rank_items(report, "revenue")
    _, notes = _normalized_report_items(report)
    return MonthlyItemSalesMetrics(**_context(report), items=items, data_quality_notes=notes)


def _share(amount: int, total: int) -> Decimal | None:
    if total <= 0:
        return None
    return (Decimal(amount) * 100 / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_monthly_sales_concentration(db: Session, location_id: int, year: int, month: int, top_n: int = 5):
    report = _analysis_report(db, location_id, year, month)
    _positive_integer(top_n, "top_n")
    rows, notes = _normalized_report_items(report)
    top_sales = sum(row.sales_amount for row in sorted(rows, key=lambda row: -row.sales_amount)[:top_n])
    if report.item_sales_amount <= 0:
        notes.append("Revenue share is undefined when the report's Items total is zero or negative.")
    return MonthlySalesConcentration(
        **_context(report), top_n=top_n, top_n_sales=top_sales,
        total_item_sales=report.item_sales_amount,
        revenue_share_percent=_share(top_sales, report.item_sales_amount) if rows else None,
        data_quality_notes=notes,
    )


def _category_rows(report):
    return [MonthlyCategoryPerformance(
        category_name=clean_report_label(row.category_name), raw_category_name=row.category_name,
        quantity=float(row.quantity), sales_amount=row.sales_amount,
        classification=classify_category(row.category_name),
    ) for row in sorted(report.category_sales, key=lambda row: (
        -row.sales_amount, -row.quantity, row.category_name.casefold(), row.category_name,
    ))]


def get_monthly_category_breakdown(db: Session, location_id: int, year: int, month: int):
    report = _analysis_report(db, location_id, year, month)
    rows = _category_rows(report)
    return MonthlyCategoryBreakdown(
        **_context(report),
        menu_categories=[r for r in rows if r.classification == "menu_category"],
        routing_categories=[r for r in rows if r.classification == "operational_routing"],
        uncategorized=[r for r in rows if r.classification == "uncategorized"],
        unknown=[r for r in rows if r.classification == "unknown"],
    )


def get_monthly_routing_mix(db: Session, location_id: int, year: int, month: int):
    report = _analysis_report(db, location_id, year, month)
    rows = [r for r in _category_rows(report) if r.classification == "operational_routing"]
    total = sum(row.sales_amount for row in rows)
    return MonthlyRoutingMix(
        **_context(report), total_routing_sales=total,
        categories=[MonthlyRoutingCategory(**row.model_dump(), revenue_share_percent=_share(row.sales_amount, total)) for row in rows],
        data_quality_notes=(
            ["No operational routing categories were reported."] if not rows
            else ["Routing shares are undefined when routing sales total is zero or negative."] if total <= 0
            else []
        ),
    )


def get_monthly_category_performance(
    db: Session,
    location_id: int,
    year: int,
    month: int,
) -> list[MonthlyCategoryPerformance]:
    """Return monthly category totals sorted by sales amount descending."""

    report = _report_for_month(db, location_id, year, month)
    if report is None:
        raise MonthlyReportNotFoundError(
            f"No Square monthly report was found for {year}-{month:02d}."
        )

    rows = sorted(
        report.category_sales,
        key=lambda row: (
            -row.sales_amount,
            -_float_quantity(row.quantity),
            row.category_name.casefold(),
        ),
    )
    return [
        MonthlyCategoryPerformance(
            category_name=row.category_name,
            quantity=_float_quantity(row.quantity),
            sales_amount=row.sales_amount,
            classification=classify_category(row.category_name),
        )
        for row in rows
    ]


def get_monthly_discount_summary(
    db: Session,
    location_id: int,
    year: int,
    month: int,
) -> MonthlyDiscountSummary:
    """Return total discount amount and the per-discount usage details."""

    report = _report_for_month(db, location_id, year, month)
    if report is None:
        raise MonthlyReportNotFoundError(
            f"No Square monthly report was found for {year}-{month:02d}."
        )

    location = _location_or_raise(db, location_id)
    discounts = [
        MonthlyDiscountDetail(
            discount_name=row.discount_name,
            usage_count=row.usage_count,
            amount=row.amount,
        )
        for row in report.discount_summaries
    ]
    return MonthlyDiscountSummary(
        location_id=location_id,
        year=year,
        month=month,
        currency=location.currency,
        total_discount_amount=report.discount_comp_amount,
        discounts=discounts,
    )


def get_latest_square_report(
    db: Session,
    location_id: int,
) -> LatestSquareReport:
    """Return the newest imported Square sales report and its key summary values."""

    _location_or_raise(db, location_id)
    report = db.scalar(
        select(models.SquareSalesReport)
        .where(models.SquareSalesReport.location_id == location_id)
        .order_by(
            models.SquareSalesReport.report_start.desc(),
            models.SquareSalesReport.id.desc(),
        )
    )
    if report is None:
        raise MonthlyReportNotFoundError(
            f"No Square sales reports have been imported for location {location_id}."
        )

    return LatestSquareReport(
        location_id=location_id,
        report_id=report.id,
        report_start=report.report_start,
        report_end=report.report_end,
        gross_sales_amount=report.gross_sales_amount,
        item_sales_amount=report.item_sales_amount,
        service_charge_amount=report.service_charge_amount,
        returns_amount=report.returns_amount,
        discount_comp_amount=report.discount_comp_amount,
        net_sales_amount=report.net_sales_amount,
        tax_amount=report.tax_amount,
        tips_amount=report.tips_amount,
        gift_card_sales_amount=report.gift_card_sales_amount,
        refund_amount=report.refund_amount,
        total_amount=report.total_amount,
        total_collected_amount=report.total_collected_amount,
        fees_amount=report.fees_amount,
        net_total_amount=report.net_total_amount,
        currency=report.location.currency,
        imported_at=report.created_at,
        created_at=report.created_at,
    )


def compare_monthly_reports(
    db: Session,
    location_id: int,
    year_a: int,
    month_a: int,
    year_b: int,
    month_b: int,
) -> MonthlyReportComparison:
    """Compare two monthly report periods deterministically and safely."""

    location = _location_or_raise(db, location_id)
    report_a = _report_for_month(db, location_id, year_a, month_a)
    report_b = _report_for_month(db, location_id, year_b, month_b)

    if report_a is None and report_b is None:
        raise MonthlyReportNotFoundError(
            "No Square monthly reports were found for either requested month."
        )

    def _value(report, field_name: str):
        if report is None:
            return None
        return getattr(report, field_name)

    def _label(report):
        if report is None:
            return None
        return report.report_start

    return MonthlyReportComparison(
        location_id=location_id,
        currency=location.currency,
        year_a=year_a,
        month_a=month_a,
        year_b=year_b,
        month_b=month_b,
        report_a_id=report_a.id if report_a else None,
        report_b_id=report_b.id if report_b else None,
        report_a_start=_label(report_a),
        report_b_start=_label(report_b),
        report_a_end=(report_a.report_end if report_a else None),
        report_b_end=(report_b.report_end if report_b else None),
        report_a_available=report_a is not None,
        report_b_available=report_b is not None,
        gross_sales_amount_a=_value(report_a, "gross_sales_amount"),
        gross_sales_amount_b=_value(report_b, "gross_sales_amount"),
        gross_sales_change=(
            _value(report_b, "gross_sales_amount")
            - _value(report_a, "gross_sales_amount")
            if report_a and report_b
            else None
        ),
        gross_sales_percentage_change=_safe_percentage_change(
            _value(report_a, "gross_sales_amount"),
            _value(report_b, "gross_sales_amount"),
        ),
        net_sales_amount_a=_value(report_a, "net_sales_amount"),
        net_sales_amount_b=_value(report_b, "net_sales_amount"),
        net_sales_change=(
            _value(report_b, "net_sales_amount")
            - _value(report_a, "net_sales_amount")
            if report_a and report_b
            else None
        ),
        net_sales_percentage_change=_safe_percentage_change(
            _value(report_a, "net_sales_amount"),
            _value(report_b, "net_sales_amount"),
        ),
        total_collected_amount_a=_value(report_a, "total_collected_amount"),
        total_collected_amount_b=_value(report_b, "total_collected_amount"),
        total_collected_change=(
            _value(report_b, "total_collected_amount")
            - _value(report_a, "total_collected_amount")
            if report_a and report_b
            else None
        ),
        total_collected_percentage_change=_safe_percentage_change(
            _value(report_a, "total_collected_amount"),
            _value(report_b, "total_collected_amount"),
        ),
        net_total_amount_a=_value(report_a, "net_total_amount"),
        net_total_amount_b=_value(report_b, "net_total_amount"),
        net_total_change=(
            _value(report_b, "net_total_amount")
            - _value(report_a, "net_total_amount")
            if report_a and report_b
            else None
        ),
        net_total_percentage_change=_safe_percentage_change(
            _value(report_a, "net_total_amount"),
            _value(report_b, "net_total_amount"),
        ),
        discount_comp_amount_a=_value(report_a, "discount_comp_amount"),
        discount_comp_amount_b=_value(report_b, "discount_comp_amount"),
        discount_comp_change=(
            _value(report_b, "discount_comp_amount")
            - _value(report_a, "discount_comp_amount")
            if report_a and report_b
            else None
        ),
        discount_comp_percentage_change=_safe_percentage_change(
            _value(report_a, "discount_comp_amount"),
            _value(report_b, "discount_comp_amount"),
        ),
        refund_amount_a=_value(report_a, "refund_amount"),
        refund_amount_b=_value(report_b, "refund_amount"),
        refund_change=(
            _value(report_b, "refund_amount")
            - _value(report_a, "refund_amount")
            if report_a and report_b
            else None
        ),
        refund_percentage_change=_safe_percentage_change(
            _value(report_a, "refund_amount"),
            _value(report_b, "refund_amount"),
        ),
        fees_amount_a=_value(report_a, "fees_amount"),
        fees_amount_b=_value(report_b, "fees_amount"),
        fees_change=(
            _value(report_b, "fees_amount")
            - _value(report_a, "fees_amount")
            if report_a and report_b
            else None
        ),
        fees_percentage_change=_safe_percentage_change(
            _value(report_a, "fees_amount"),
            _value(report_b, "fees_amount"),
        ),
        tips_amount_a=_value(report_a, "tips_amount"),
        tips_amount_b=_value(report_b, "tips_amount"),
        tips_change=(
            _value(report_b, "tips_amount")
            - _value(report_a, "tips_amount")
            if report_a and report_b
            else None
        ),
        tips_percentage_change=_safe_percentage_change(
            _value(report_a, "tips_amount"),
            _value(report_b, "tips_amount"),
        ),
    )


def get_data_coverage(db: Session, location_id: int) -> MonthlyDataCoverage:
    """Describe the monthly aggregate data available for a location."""

    location = _location_or_raise(db, location_id)
    reports = list(
        db.scalars(
            select(models.SquareSalesReport)
            .where(models.SquareSalesReport.location_id == location_id)
            .order_by(
                models.SquareSalesReport.report_start.desc(),
                models.SquareSalesReport.id.desc(),
            )
        ).all()
    )

    latest_report = reports[0] if reports else None
    has_monthly_reports = bool(reports)
    provenance_values = set(
        db.scalars(
            select(models.Order.provenance).distinct()
            .where(models.Order.location_id == location_id)
        ).all()
    )
    has_real_transaction_data = bool(provenance_values.intersection(REAL_PROVENANCE))
    demo_transaction_data_present = "demo" in provenance_values
    real_granularity = (["monthly_aggregate"] if has_monthly_reports else []) + (
        ["daily", "transaction"] if has_real_transaction_data else []
    )

    return MonthlyDataCoverage(
        location_id=location_id,
        latest_monthly_report_start=(latest_report.report_start if latest_report else None),
        latest_monthly_report_end=(latest_report.report_end if latest_report else None),
        monthly_report_count=len(reports),
        has_monthly_reports=has_monthly_reports,
        has_real_transaction_data=has_real_transaction_data,
        available_granularity=(
            (["monthly_aggregate"] if has_monthly_reports else [])
            + (["transaction_level"] if has_real_transaction_data else [])
        ),
        demo_transaction_data_present=demo_transaction_data_present,
        has_demo_transaction_data=demo_transaction_data_present,
        has_unknown_transaction_data="unknown" in provenance_values,
        available_real_granularity=real_granularity,
        available_demo_granularity=(["daily", "transaction"] if demo_transaction_data_present else []),
    )
