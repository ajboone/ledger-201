from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.square_sales_report_schemas import (
    SquareSalesReportImportRequest,
    SquareSalesReportImportResult,
    SquareSalesReportRead,
    SquareSalesReportSummary,
)
from app.services.square_sales_report_import import (
    DuplicateSquareSalesReportError,
    SquareSalesReportLocationNotFoundError,
    get_square_sales_report,
    import_square_sales_report,
    list_square_sales_reports,
)
from app.services.square_sales_report_parser import SquareSalesReportParseError


router = APIRouter(
    prefix="/api/square-reports",
    tags=["square-reports"],
)


@router.post(
    "/import",
    response_model=SquareSalesReportImportResult,
    status_code=status.HTTP_201_CREATED,
)
def create_square_sales_report_import(
    import_request: SquareSalesReportImportRequest,
    db: Session = Depends(get_db),
) -> SquareSalesReportImportResult:
    """Import aggregate Square report text as a single atomic report."""

    try:
        outcome = import_square_sales_report(
            db,
            import_request.location_id,
            import_request.raw_report_text,
        )
    except SquareSalesReportLocationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except DuplicateSquareSalesReportError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except SquareSalesReportParseError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    report = outcome.report
    return SquareSalesReportImportResult(
        report_id=report.id,
        report_start=report.report_start,
        report_end=report.report_end,
        categories_imported=len(report.category_sales),
        items_imported=len(report.item_sales),
        discounts_imported=len(report.discount_summaries),
        warnings=outcome.warnings,
    )


@router.get(
    "",
    response_model=list[SquareSalesReportSummary],
)
def read_square_sales_reports(
    location_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> list[models.SquareSalesReport]:
    """List aggregate reports, optionally filtered to one Ledger location."""

    return list_square_sales_reports(db, location_id)


@router.get(
    "/{report_id}",
    response_model=SquareSalesReportRead,
)
def read_square_sales_report(
    report_id: int,
    db: Session = Depends(get_db),
) -> models.SquareSalesReport:
    """Return one report summary and its category, item, and discount rows."""

    report = get_square_sales_report(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Square sales report not found.",
        )
    return report
