from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VendorCreate(BaseModel):
    """Data accepted when creating a vendor."""

    name: str = Field(
        min_length=1,
        max_length=100,
    )


class VendorRead(BaseModel):
    """Vendor data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class LocationCreate(BaseModel):
    """Data accepted when creating a restaurant location."""

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    square_location_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )

    timezone: str = Field(
        default="America/New_York",
        min_length=1,
        max_length=64,
    )

    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
    )


class LocationRead(BaseModel):
    """Location data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    square_location_id: str | None
    timezone: str
    currency: str
    is_active: bool
    created_at: datetime


class OrderLineItemCreate(BaseModel):
    """Data accepted when creating a single line item on an order."""

    square_line_item_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    catalog_object_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    item_name: str = Field(
        min_length=1,
        max_length=200,
    )
    variation_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    category_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    quantity: int = Field(..., gt=0)
    unit_price_amount: int = Field(..., ge=0)
    gross_sales_amount: int = Field(..., ge=0)
    discount_amount: int = Field(default=0, ge=0)
    total_amount: int = Field(..., ge=0)

    @field_validator(
        "square_line_item_id",
        "catalog_object_id",
        "item_name",
        "variation_name",
        "category_name",
        mode="before",
    )
    @classmethod
    def strip_optional_text(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_line_item_totals(self):
        expected_total = self.gross_sales_amount - self.discount_amount
        if self.total_amount != expected_total:
            raise ValueError(
                "Line item total must equal gross sales minus discount."
            )

        expected_gross = self.quantity * self.unit_price_amount
        if self.gross_sales_amount != expected_gross:
            raise ValueError(
                "Gross sales must equal quantity multiplied by unit price."
            )

        return self


class OrderLineItemRead(BaseModel):
    """Nested line item data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    square_line_item_id: str | None
    catalog_object_id: str | None
    item_name: str
    variation_name: str | None
    category_name: str | None
    quantity: int
    unit_price_amount: int
    gross_sales_amount: int
    discount_amount: int
    total_amount: int


class OrderCreate(BaseModel):
    """Data accepted when creating an order and its line items."""

    location_id: int = Field(..., gt=0)
    square_order_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    state: str = Field(
        default="OPEN",
        min_length=1,
        max_length=32,
    )
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
    )
    created_at: datetime | None = None
    closed_at: datetime | None = None
    subtotal_amount: int = Field(..., ge=0)
    discount_amount: int = Field(default=0, ge=0)
    tax_amount: int = Field(default=0, ge=0)
    service_charge_amount: int = Field(default=0, ge=0)
    total_amount: int = Field(..., ge=0)
    line_items: list[OrderLineItemCreate] = Field(default_factory=list)

    @field_validator("square_order_id", "state", "currency", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_order_totals(self):
        if self.discount_amount > self.subtotal_amount:
            raise ValueError("Order discount cannot exceed the subtotal.")

        expected_total = (
            self.subtotal_amount
            - self.discount_amount
            + self.tax_amount
            + self.service_charge_amount
        )
        if self.total_amount != expected_total:
            raise ValueError(
                "Order total must equal subtotal minus discount plus tax and service charge."
            )
        return self


class OrderRead(BaseModel):
    """Order data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    square_order_id: str | None
    location_id: int
    state: str
    currency: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    subtotal_amount: int
    discount_amount: int
    tax_amount: int
    service_charge_amount: int
    total_amount: int
    line_items: list[OrderLineItemRead]


class PaymentCreate(BaseModel):
    """Data accepted when recording a payment applied to an order."""

    order_id: int = Field(..., gt=0)
    square_payment_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    status: str = Field(min_length=1, max_length=32)
    source_type: str | None = Field(default=None, min_length=1, max_length=32)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    amount: int = Field(..., gt=0)
    created_at: datetime | None = None

    @field_validator(
        "status",
        "currency",
        "source_type",
        mode="before",
    )
    @classmethod
    def normalize_payment_text(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized.upper() if normalized else None

    @field_validator("square_payment_id", mode="before")
    @classmethod
    def normalize_square_payment_id(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("status")
    @classmethod
    def validate_payment_status(cls, value: str) -> str:
        if value not in {"COMPLETED", "APPROVED", "PENDING", "FAILED", "CANCELED"}:
            raise ValueError("Unsupported payment status.")
        return value


class PaymentSummaryRead(BaseModel):
    """Compact payment details embedded in a refund response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    square_payment_id: str | None
    status: str
    currency: str
    amount: int


class PaymentRead(BaseModel):
    """Payment data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    square_payment_id: str | None
    status: str
    source_type: str | None
    currency: str
    amount: int
    created_at: datetime
    updated_at: datetime


class RefundCreate(BaseModel):
    """Data accepted when recording a refund against a payment."""

    payment_id: int = Field(..., gt=0)
    square_refund_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    status: str = Field(min_length=1, max_length=32)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    amount: int = Field(..., gt=0)
    reason: str | None = Field(default=None, min_length=1, max_length=200)
    created_at: datetime | None = None

    @field_validator(
        "status",
        "currency",
        mode="before",
    )
    @classmethod
    def normalize_refund_text(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized.upper() if normalized else None

    @field_validator("square_refund_id", "reason", mode="before")
    @classmethod
    def normalize_refund_optional_text(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("status")
    @classmethod
    def validate_refund_status(cls, value: str) -> str:
        if value not in {"COMPLETED", "PENDING", "FAILED"}:
            raise ValueError("Unsupported refund status.")
        return value


class RefundRead(BaseModel):
    """Refund data returned with its compact associated payment."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_id: int
    square_refund_id: str | None
    status: str
    currency: str
    amount: int
    reason: str | None
    created_at: datetime
    updated_at: datetime
    payment: PaymentSummaryRead


class OrderReconciliation(BaseModel):
    """Order-level payment reconciliation included in a daily review."""

    order_id: int
    square_order_id: str | None
    order_total_amount: int
    completed_payment_amount: int
    completed_refund_amount: int
    net_collected_amount: int
    difference: int
    status: str


class ItemSummary(BaseModel):
    """Sales summary for one menu item on the review date."""

    item_name: str
    quantity_sold: int
    gross_sales_amount: int
    total_sales_amount: int


class DailyReview(BaseModel):
    """Calculated financial and item summary for a location and local date."""

    location_id: int
    location_name: str
    currency: str
    review_date: date
    order_count: int
    subtotal_amount: int
    discount_amount: int
    tax_amount: int
    service_charge_amount: int
    order_total_amount: int
    completed_payment_amount: int
    completed_refund_amount: int
    net_collected_amount: int
    average_order_value: int
    reconciliation_difference: int
    reconciliation_status: str
    orders: list[OrderReconciliation]
    top_items: list[ItemSummary]