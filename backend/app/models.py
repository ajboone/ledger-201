from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
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
