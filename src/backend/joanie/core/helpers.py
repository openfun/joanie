"""
Helpers that can be useful throughout Joanie's core app
"""

from joanie.core import enums


def generate_certificates_for_orders(orders):
    """
    Iterate over the provided orders and check if they are eligible for certification
    then return the count of generated certificates.
    """
    total = 0
    orders_filtered = (
        orders.filter(
            state=enums.ORDER_STATE_VALIDATED,
            certificate__isnull=True,
            product__type__in=enums.PRODUCT_TYPE_CERTIFICATE_ALLOWED,
        )
        .select_related("product")
        .iterator()
    )

    for order in orders_filtered:
        _certificate, created = order.get_or_generate_certificate()
        if created is True:
            total += 1

    return total
