from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas


class PaymentServiceError(Exception):
    """Base class for expected payment/refund domain errors."""


class OrderNotFoundError(PaymentServiceError):
    """Raised when a payment references an unknown order."""


class PaymentNotFoundError(PaymentServiceError):
    """Raised when a refund references an unknown payment."""


class DuplicateSquarePaymentError(PaymentServiceError):
    """Raised when a Square payment ID is already assigned."""


class DuplicateSquareRefundError(PaymentServiceError):
    """Raised when a Square refund ID is already assigned."""


class PaymentCurrencyMismatchError(PaymentServiceError):
    """Raised when a payment currency differs from its order currency."""


class RefundCurrencyMismatchError(PaymentServiceError):
    """Raised when a refund currency differs from its payment currency."""


class PaymentNotRefundableError(PaymentServiceError):
    """Raised when refunding a payment that has not completed."""


class RefundLimitExceededError(PaymentServiceError):
    """Raised when the requested refund exceeds the remaining refundable amount."""


_REFUNDABLE_STATUSES = ("COMPLETED", "PENDING")


def create_payment(db: Session, payment_data: schemas.PaymentCreate) -> models.Payment:
    """Create a payment associated with an existing order in one transaction."""

    try:
        order = db.get(models.Order, payment_data.order_id)
        if order is None:
            raise OrderNotFoundError("Order not found.")

        if order.currency != payment_data.currency:
            raise PaymentCurrencyMismatchError(
                "Payment currency must match the order currency."
            )

        square_payment_id = payment_data.square_payment_id or None
        if square_payment_id is not None:
            existing_payment = db.scalar(
                select(models.Payment).where(
                    models.Payment.square_payment_id == square_payment_id
                )
            )
            if existing_payment is not None:
                raise DuplicateSquarePaymentError(
                    "This Square payment ID is already in use."
                )

        payment = models.Payment(
            order=order,
            square_payment_id=square_payment_id,
            status=payment_data.status,
            source_type=payment_data.source_type,
            currency=payment_data.currency,
            amount=payment_data.amount,
            created_at=payment_data.created_at,
        )
        db.add(payment)
        db.flush()
        db.commit()
        return payment
    except IntegrityError as error:
        db.rollback()
        if payment_data.square_payment_id is not None:
            existing_payment = db.scalar(
                select(models.Payment).where(
                    models.Payment.square_payment_id
                    == payment_data.square_payment_id
                )
            )
            if existing_payment is not None:
                raise DuplicateSquarePaymentError(
                    "This Square payment ID is already in use."
                ) from error
        raise
    except Exception:
        db.rollback()
        raise


def create_refund(db: Session, refund_data: schemas.RefundCreate) -> models.Refund:
    """Create a refund atomically after checking its refundable balance."""

    try:
        payment = db.scalar(
            select(models.Payment)
            .where(models.Payment.id == refund_data.payment_id)
            .with_for_update()
        )
        if payment is None:
            raise PaymentNotFoundError("Payment not found.")

        if payment.status != "COMPLETED":
            raise PaymentNotRefundableError(
                "Refunds can only be created for completed payments."
            )

        if payment.currency != refund_data.currency:
            raise RefundCurrencyMismatchError(
                "Refund currency must match the payment currency."
            )

        square_refund_id = refund_data.square_refund_id or None
        if square_refund_id is not None:
            existing_refund = db.scalar(
                select(models.Refund).where(
                    models.Refund.square_refund_id == square_refund_id
                )
            )
            if existing_refund is not None:
                raise DuplicateSquareRefundError(
                    "This Square refund ID is already in use."
                )

        if refund_data.amount > payment.amount:
            raise RefundLimitExceededError(
                "Refund amount cannot exceed the payment amount."
            )

        if refund_data.status in _REFUNDABLE_STATUSES:
            reserved_amount = db.scalar(
                select(func.coalesce(func.sum(models.Refund.amount), 0)).where(
                    models.Refund.payment_id == payment.id,
                    models.Refund.status.in_(_REFUNDABLE_STATUSES),
                )
            )
            if reserved_amount + refund_data.amount > payment.amount:
                raise RefundLimitExceededError(
                    "Completed and pending refunds cannot exceed the payment amount."
                )

        refund = models.Refund(
            payment=payment,
            square_refund_id=square_refund_id,
            status=refund_data.status,
            currency=refund_data.currency,
            amount=refund_data.amount,
            reason=refund_data.reason,
            created_at=refund_data.created_at,
        )
        db.add(refund)
        db.flush()
        db.commit()
        return refund
    except IntegrityError as error:
        db.rollback()
        if refund_data.square_refund_id is not None:
            existing_refund = db.scalar(
                select(models.Refund).where(
                    models.Refund.square_refund_id == refund_data.square_refund_id
                )
            )
            if existing_refund is not None:
                raise DuplicateSquareRefundError(
                    "This Square refund ID is already in use."
                ) from error
        raise
    except Exception:
        db.rollback()
        raise
