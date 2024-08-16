"""Utility to prepare email context data variables for installment payments"""

import smtplib
from logging import getLogger

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from stockholm import Money

from joanie.core.enums import (
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUSED,
)

logger = getLogger(__name__)


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
            order.get_installment_index(state=PAYMENT_STATE_REFUSED)
            if payment_refused
            else order.get_installment_index(state=PAYMENT_STATE_PAID)
        ),
    }

    if not payment_refused:
        variable_context_part = {
            "remaining_balance_to_pay": order.get_remaining_balance_to_pay(),
            "date_next_installment_to_pay": order.get_date_next_installment_to_pay(),
        }
        context_data.update(variable_context_part)

    return context_data


def prepare_context_for_upcoming_installment(
    order, installment_amount, product_title, days_until_debit
):
    """
    Prepare the context variables for the email when an upcoming installment payment
    will be soon debited for a user.
    """
    context_data = prepare_context_data(
        order, installment_amount, product_title, payment_refused=False
    )
    context_data["targeted_installment_index"] = order.get_installment_index(
        state=PAYMENT_STATE_PENDING, find_first=True
    )
    context_data["days_until_debit"] = days_until_debit

    return context_data


def send(subject, template_vars, template_name, to_user_email):
    """Send a mail to the user"""
    try:
        msg_html = render_to_string(f"mail/html/{template_name}.html", template_vars)
        msg_plain = render_to_string(f"mail/text/{template_name}.txt", template_vars)
        send_mail(
            subject,
            msg_plain,
            settings.EMAIL_FROM,
            [to_user_email],
            html_message=msg_html,
            fail_silently=False,
        )
    except smtplib.SMTPException as exception:
        # no exception raised as user can't sometimes change his mail,
        logger.error("%s purchase order mail %s not send", to_user_email, exception)
