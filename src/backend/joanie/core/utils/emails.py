"""Utility to prepare email context data variables for installment payments"""

from django.conf import settings

from stockholm import Money

from joanie.core.enums import PAYMENT_STATE_PAID, PAYMENT_STATE_REFUSED


def prepare_context_data(
    order, installment_amount, product_title, payment_refused: bool
):
    """
    Prepare the context variables for the email when an installment has been paid
    or refused.
    """
    context_data = {
        "fullname": order.owner.get_full_name() or order.owner.username,
        "email": order.owner.email,
        "product_title": product_title,
        "installment_amount": Money(installment_amount),
        "product_price": Money(order.product.price),
        "credit_card_last_numbers": order.credit_card.last_numbers,
        "order_payment_schedule": order.payment_schedule,
        "dashboard_order_link": (
            settings.JOANIE_DASHBOARD_ORDER_LINK.replace(":orderId", str(order.id))
        ),
        "site": {
            "name": settings.JOANIE_CATALOG_NAME,
            "url": settings.JOANIE_CATALOG_BASE_URL,
        },
        "targeted_installment_index": (
            order.get_index_of_last_installment(state=PAYMENT_STATE_REFUSED)
            if payment_refused
            else order.get_index_of_last_installment(state=PAYMENT_STATE_PAID)
        ),
    }

    if not payment_refused:
        variable_context_part = {
            "remaining_balance_to_pay": order.get_remaining_balance_to_pay(),
            "date_next_installment_to_pay": order.get_date_next_installment_to_pay(),
        }
        context_data.update(variable_context_part)

    return context_data
