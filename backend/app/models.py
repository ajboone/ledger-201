from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Vendor(Base):
    """A company or supplier that the restaurant purchases from."""

    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Location(Base):
    """A restaurant location represented in Ledger 201."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    square_location_id: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True,
    )

    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="America/New_York",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    orders: Mapped[list["Order"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
    )

    square_sales_reports: Mapped[list["SquareSalesReport"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
    )


class SquareSalesReport(Base):
    """Aggregate sales-report data imported from Square."""

    __tablename__ = "square_sales_reports"
    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "report_start",
            "report_end",
            name="uq_square_sales_reports_location_period",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"),
        nullable=False,
        index=True,
    )
    report_start: Mapped[date] = mapped_column(Date, nullable=False)
    report_end: Mapped[date] = mapped_column(Date, nullable=False)
    report_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Square Sales Report",
    )

    gross_sales_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    item_sales_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    service_charge_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    returns_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_comp_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    net_sales_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    tips_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    gift_card_sales_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    refund_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    total_collected_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    fees_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    net_total_amount: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    location: Mapped[Location] = relationship(
        back_populates="square_sales_reports",
    )
    category_sales: Mapped[list["SquareCategorySales"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by=lambda: SquareCategorySales.id,
    )
    item_sales: Mapped[list["SquareItemSales"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by=lambda: SquareItemSales.id,
    )
    discount_summaries: Mapped[list["SquareDiscountSummary"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by=lambda: SquareDiscountSummary.id,
    )


class SquareCategorySales(Base):
    """Aggregate quantity and sales for a Square report category."""

    __tablename__ = "square_category_sales"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_square_category_quantity_nonnegative"),
        CheckConstraint(
            "length(trim(category_name)) > 0",
            name="ck_square_category_name_nonempty",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("square_sales_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    sales_amount: Mapped[int] = mapped_column(Integer, nullable=False)

    report: Mapped[SquareSalesReport] = relationship(
        back_populates="category_sales",
    )


class SquareItemSales(Base):
    """Aggregate quantity and sales for a Square report item/variation."""

    __tablename__ = "square_item_sales"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_square_item_quantity_nonnegative"),
        CheckConstraint(
            "length(trim(item_name)) > 0",
            name="ck_square_item_name_nonempty",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("square_sales_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    variation_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    sales_amount: Mapped[int] = mapped_column(Integer, nullable=False)

    report: Mapped[SquareSalesReport] = relationship(
        back_populates="item_sales",
    )


class SquareDiscountSummary(Base):
    """Aggregate usage and amount for a Square report discount."""

    __tablename__ = "square_discount_summaries"
    __table_args__ = (
        CheckConstraint(
            "usage_count >= 0",
            name="ck_square_discount_usage_count_nonnegative",
        ),
        CheckConstraint(
            "length(trim(discount_name)) > 0",
            name="ck_square_discount_name_nonempty",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("square_sales_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    discount_name: Mapped[str] = mapped_column(String(200), nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    report: Mapped[SquareSalesReport] = relationship(
        back_populates="discount_summaries",
    )


class Order(Base):
    """A restaurant sales order tied to a specific location."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("subtotal_amount >= 0", name="ck_orders_subtotal_nonnegative"),
        CheckConstraint("discount_amount >= 0", name="ck_orders_discount_nonnegative"),
        CheckConstraint("tax_amount >= 0", name="ck_orders_tax_nonnegative"),
        CheckConstraint(
            "service_charge_amount >= 0",
            name="ck_orders_service_charge_nonnegative",
        ),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        CheckConstraint(
            "discount_amount <= subtotal_amount",
            name="ck_orders_discount_within_subtotal",
        ),
        CheckConstraint(
            "total_amount = subtotal_amount - discount_amount + tax_amount "
            "+ service_charge_amount",
            name="ck_orders_total_matches_components",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    square_order_id: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True,
    )

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"),
        nullable=False,
        index=True,
    )

    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="OPEN",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    subtotal_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    discount_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    tax_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    service_charge_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    location: Mapped[Location] = relationship(
        back_populates="orders",
    )

    line_items: Mapped[list["OrderLineItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderLineItem(Base):
    """A single line entry within an order."""

    __tablename__ = "order_line_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_line_items_quantity_positive"),
        CheckConstraint(
            "unit_price_amount >= 0",
            name="ck_order_line_items_unit_price_nonnegative",
        ),
        CheckConstraint(
            "gross_sales_amount >= 0",
            name="ck_order_line_items_gross_nonnegative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_order_line_items_discount_nonnegative",
        ),
        CheckConstraint(
            "discount_amount <= gross_sales_amount",
            name="ck_order_line_items_discount_within_gross",
        ),
        CheckConstraint("total_amount >= 0", name="ck_order_line_items_total_nonnegative"),
        CheckConstraint(
            "gross_sales_amount = quantity * unit_price_amount",
            name="ck_order_line_items_gross_matches_quantity",
        ),
        CheckConstraint(
            "total_amount = gross_sales_amount - discount_amount",
            name="ck_order_line_items_total_matches_components",
        ),
        CheckConstraint(
            "length(trim(item_name)) > 0",
            name="ck_order_line_items_name_nonempty",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    square_line_item_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    catalog_object_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    item_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    variation_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    category_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_price_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    gross_sales_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    discount_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    order: Mapped[Order] = relationship(
        back_populates="line_items",
    )


class Payment(Base):
    """A payment amount applied to an order, excluding tips and processor fees."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint("currency GLOB '[A-Z][A-Z][A-Z]'", name="ck_payments_currency"),
        CheckConstraint(
            "status IN ('COMPLETED', 'APPROVED', 'PENDING', 'FAILED', 'CANCELED')",
            name="ck_payments_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    square_payment_id: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    source_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    order: Mapped[Order] = relationship(
        back_populates="payments",
    )

    refunds: Mapped[list["Refund"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
    )


class Refund(Base):
    """A refund amount returned against a payment, stored in minor units."""

    __tablename__ = "refunds"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_refunds_amount_positive"),
        CheckConstraint("currency GLOB '[A-Z][A-Z][A-Z]'", name="ck_refunds_currency"),
        CheckConstraint(
            "status IN ('COMPLETED', 'PENDING', 'FAILED')",
            name="ck_refunds_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    square_refund_id: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    payment: Mapped[Payment] = relationship(
        back_populates="refunds",
    )
