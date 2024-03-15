"""
Helpers that can be useful throughout Joanie's core app
"""

from django.db.models.query import QuerySet

from joanie.core import enums, models
from joanie.core.exceptions import CertificateGenerationError


def generate_certificates_for_orders(orders):
    """
    Iterate over the provided orders and check if they are eligible for certification
    then return the count of generated certificates.
    """
    total = 0
    if isinstance(orders, QuerySet):
        orders_queryset = orders
    elif isinstance(orders, list):
        orders_queryset = models.Order.objects.filter(pk__in=orders)
    else:
        raise ValueError("orders must be either List or QuerySet")

    orders_filtered = (
        orders_queryset.filter(
            state=enums.ORDER_STATE_VALIDATED,
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
