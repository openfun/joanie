"""
Helpers that can be useful throughout Joanie's core app
"""

import logging

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet

from joanie.core import enums
from joanie.core.exceptions import CertificateGenerationError
from joanie.payment import get_payment_backend

logger = logging.getLogger(__name__)


def generate_certificates_for_orders(orders):
    """
    Iterate over the provided orders and check if they are eligible for certification
    then return the count of generated certificates.
    """
    total = 0
    if isinstance(orders, QuerySet):
        orders_queryset = orders
    elif isinstance(orders, list):
        Order = apps.get_model("core", "Order")  # pylint: disable=invalid-name
        orders_queryset = Order.objects.filter(pk__in=orders)
    else:
        raise ValueError("orders must be either List or QuerySet")

    orders_filtered = (
        orders_queryset.filter(
            state=enums.ORDER_STATE_COMPLETED,
            certificate__isnull=True,
            product__type__in=enums.PRODUCT_TYPE_CERTIFICATE_ALLOWED,
        )
        .select_related("product")
        .iterator()
    )

    for order in orders_filtered:
        try:
            _certificate, created = order.get_or_generate_certificate()
        except CertificateGenerationError:
            created = False

        if created is True:
            total += 1

    return total


def send_mail_vouchers(batch_order_id: str):
    """Send an email to batch order's owner with vouchers into the owner's language."""

    BatchOrder = apps.get_model("core", "BatchOrder")  # pylint: disable=invalid-name
    batch_order = BatchOrder.objects.get(pk=batch_order_id)

    payment_backend = get_payment_backend()
    # pylint:disable=protected-access
    payment_backend._send_mail_batch_order_payment_success(  # noqa: SLF001
        batch_order, batch_order.total, batch_order.vouchers
    )


def generate_orders(batch_order_id: str):
    """
    Generate orders and vouchers once the batch order has been paid.
    """
    # pylint: disable=invalid-name
    BatchOrder = apps.get_model("core", "BatchOrder")
    Discount = apps.get_model("core", "Discount")
    Order = apps.get_model("core", "Order")
    Voucher = apps.get_model("core", "Voucher")

    batch_order = BatchOrder.objects.get(pk=batch_order_id)
    if not batch_order.is_paid:
        message = "The batch order is not yet paid."
        logger.error(
            message,
            extra={
                "context": {
                    "batch_order": batch_order.to_dict(),
                    "relation": batch_order.relation.to_dict(),
                }
            },
        )
        raise ValidationError(message)

    discount, _ = Discount.objects.get_or_create(rate=1)

    for _ in range(batch_order.nb_seats):
        order = Order.objects.create(
            owner=None,
            product=batch_order.relation.product,
            course=batch_order.relation.course,
            organization=batch_order.organization,
        )
        if batch_order.offering_rules.exists():
            order.offering_rules.add(batch_order.offering_rules.first())

        order.voucher = Voucher.objects.create(
            discount=discount, multiple_use=False, multiple_users=False
        )
        order.flow.assign()
        batch_order.orders.add(order)
        order.flow.update()
