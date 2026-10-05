from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import models
from app.services.square_sales_report_parser import (
    ParsedSquareSalesReport,
    parse_square_sales_report,
)


class SquareSalesReportImportError(Exception):
    """Base class for expected aggregate Square report import errors."""


class SquareSalesReportLocationNotFoundError(SquareSalesReportImportError):
    """Raised when an import references a location that does not exist."""


class DuplicateSquareSalesReportError(SquareSalesReportImportError):
    """Raised when a location already has a report for the same date period."""


@dataclass(frozen=True)
class SquareSalesReportImportOutcome:
    report: models.SquareSalesReport
    warnings: list[str]


def import_square_sales_report(
    db: Session,
    location_id: int,
    raw_report_text: str,
) -> SquareSalesReportImportOutcome:
    """Parse and persist one report atomically without fabricating transactions."""

    location = db.get(models.Location, location_id)
    if location is None:
        raise SquareSalesReportLocationNotFoundError("Location not found.")

    parsed: ParsedSquareSalesReport = parse_square_sales_report(raw_report_text)
    existing_report = db.scalar(
        select(models.SquareSalesReport).where(
            models.SquareSalesReport.location_id == location_id,
            models.SquareSalesReport.report_start == parsed.report_start,
            models.SquareSalesReport.report_end == parsed.report_end,
        )
    )
    if existing_report is not None:
        raise DuplicateSquareSalesReportError(
            "A Square sales report for this location and date period already exists."
        )

    report = models.SquareSalesReport(
        location_id=location_id,
        report_start=parsed.report_start,
        report_end=parsed.report_end,
        report_name=parsed.report_name,
        reported_at=parsed.reported_at,
        source_name="Square Sales Report",
        gross_sales_amount=parsed.gross_sales_amount,
        item_sales_amount=parsed.item_sales_amount,
        service_charge_amount=parsed.service_charge_amount,
        returns_amount=parsed.returns_amount,
        discount_comp_amount=parsed.discount_comp_amount,
        net_sales_amount=parsed.net_sales_amount,
        tax_amount=parsed.tax_amount,
        tips_amount=parsed.tips_amount,
        gift_card_sales_amount=parsed.gift_card_sales_amount,
        refund_amount=parsed.refund_amount,
        total_amount=parsed.total_amount,
        total_collected_amount=parsed.total_collected_amount,
        fees_amount=parsed.fees_amount,
        net_total_amount=parsed.net_total_amount,
        category_sales=[
            models.SquareCategorySales(
                category_name=row.category_name,
                quantity=row.quantity,
                sales_amount=row.sales_amount,
            )
            for row in parsed.categories
        ],
        item_sales=[
            models.SquareItemSales(
                item_name=row.item_name,
                variation_name=row.variation_name,
                quantity=row.quantity,
                sales_amount=row.sales_amount,
            )
            for row in parsed.items
        ],
        discount_summaries=[
            models.SquareDiscountSummary(
                discount_name=row.discount_name,
                usage_count=row.usage_count,
                amount=row.amount,
            )
            for row in parsed.discounts
        ],
    )

    try:
        db.add(report)
        db.flush()
        db.commit()
        db.refresh(report)
    except IntegrityError as error:
        db.rollback()
        concurrent_duplicate = db.scalar(
            select(models.SquareSalesReport.id).where(
                models.SquareSalesReport.location_id == location_id,
                models.SquareSalesReport.report_start == parsed.report_start,
                models.SquareSalesReport.report_end == parsed.report_end,
            )
        )
        if concurrent_duplicate is not None:
            raise DuplicateSquareSalesReportError(
                "A Square sales report for this location and date period already exists."
            ) from error
        raise
    except Exception:
        db.rollback()
        raise

    return SquareSalesReportImportOutcome(report=report, warnings=parsed.warnings)


def list_square_sales_reports(
    db: Session,
    location_id: int | None = None,
) -> list[models.SquareSalesReport]:
    """Return report summaries in descending period order."""

    statement = select(models.SquareSalesReport)
    if location_id is not None:
        statement = statement.where(
            models.SquareSalesReport.location_id == location_id
        )
    statement = statement.order_by(
        models.SquareSalesReport.report_start.desc(),
        models.SquareSalesReport.id.desc(),
    )
    return list(db.scalars(statement).all())


def get_square_sales_report(
    db: Session,
    report_id: int,
) -> models.SquareSalesReport | None:
    """Return one report with all aggregate sections loaded."""

    statement = (
        select(models.SquareSalesReport)
        .options(
            selectinload(models.SquareSalesReport.category_sales),
            selectinload(models.SquareSalesReport.item_sales),
            selectinload(models.SquareSalesReport.discount_summaries),
        )
        .where(models.SquareSalesReport.id == report_id)
    )
    return db.scalar(statement)
