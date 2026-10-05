from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SquareSalesReportImportRequest(BaseModel):
    """Raw Square report text and the Ledger location it belongs to."""

    location_id: int = Field(..., gt=0)
    raw_report_text: str = Field(..., min_length=1)

    @field_validator("raw_report_text")
    @classmethod
    def require_nonblank_report_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Square report text must not be empty.")
        return normalized


class SquareCategorySalesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_name: str
    quantity: float
    sales_amount: int


class SquareItemSalesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_name: str
    variation_name: str | None
    quantity: float
    sales_amount: int


class SquareDiscountSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    discount_name: str
    usage_count: int
    amount: int


class SquareSalesReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    report_start: date
    report_end: date
    report_name: str | None
    reported_at: datetime | None
    source_name: str
    gross_sales_amount: int
    item_sales_amount: int
    service_charge_amount: int
    returns_amount: int
    discount_comp_amount: int
    net_sales_amount: int
    tax_amount: int
    tips_amount: int
    gift_card_sales_amount: int
    refund_amount: int
    total_amount: int
    total_collected_amount: int
    fees_amount: int
    net_total_amount: int
    created_at: datetime


class SquareSalesReportRead(SquareSalesReportSummary):
    """A report summary and its aggregate child rows."""

    category_sales: list[SquareCategorySalesRead]
    item_sales: list[SquareItemSalesRead]
    discount_summaries: list[SquareDiscountSummaryRead]


class SquareSalesReportImportResult(BaseModel):
    report_id: int
    report_start: date
    report_end: date
    categories_imported: int
    items_imported: int
    discounts_imported: int
    warnings: list[str]
