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


class MonthlyReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location_id: int
    report_id: int
    report_start: date
    report_end: date
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
    currency: str
    imported_at: datetime | None
    created_at: datetime


class MonthlyTopItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_name: str
    variation_name: str | None = None
    quantity: float
    sales_amount: int
    rank: int


class MonthlyCategoryPerformance(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_name: str
    quantity: float
    sales_amount: int


class MonthlyDiscountDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    discount_name: str
    usage_count: int
    amount: int


class MonthlyDiscountSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location_id: int
    year: int
    month: int
    currency: str
    total_discount_amount: int
    discounts: list[MonthlyDiscountDetail] = []


class LatestSquareReport(MonthlyReportSummary):
    pass


class MonthlyReportComparison(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location_id: int
    currency: str
    year_a: int
    month_a: int
    year_b: int
    month_b: int
    report_a_id: int | None = None
    report_b_id: int | None = None
    report_a_start: date | None = None
    report_b_start: date | None = None
    report_a_end: date | None = None
    report_b_end: date | None = None
    report_a_available: bool = True
    report_b_available: bool = True
    gross_sales_amount_a: int | None = None
    gross_sales_amount_b: int | None = None
    gross_sales_change: int | None = None
    gross_sales_percentage_change: float | None = None
    net_sales_amount_a: int | None = None
    net_sales_amount_b: int | None = None
    net_sales_change: int | None = None
    net_sales_percentage_change: float | None = None
    total_collected_amount_a: int | None = None
    total_collected_amount_b: int | None = None
    total_collected_change: int | None = None
    total_collected_percentage_change: float | None = None
    net_total_amount_a: int | None = None
    net_total_amount_b: int | None = None
    net_total_change: int | None = None
    net_total_percentage_change: float | None = None
    discount_comp_amount_a: int | None = None
    discount_comp_amount_b: int | None = None
    discount_comp_change: int | None = None
    discount_comp_percentage_change: float | None = None
    refund_amount_a: int | None = None
    refund_amount_b: int | None = None
    refund_change: int | None = None
    refund_percentage_change: float | None = None
    fees_amount_a: int | None = None
    fees_amount_b: int | None = None
    fees_change: int | None = None
    fees_percentage_change: float | None = None
    tips_amount_a: int | None = None
    tips_amount_b: int | None = None
    tips_change: int | None = None
    tips_percentage_change: float | None = None


class MonthlyDataCoverage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location_id: int
    latest_monthly_report_start: date | None = None
    latest_monthly_report_end: date | None = None
    monthly_report_count: int
    has_monthly_reports: bool
    has_real_transaction_data: bool
    available_granularity: list[str] = []
    demo_transaction_data_present: bool = False
