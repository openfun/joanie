"""Utility to prepare email context data variables for installment payments"""

import smtplib
from logging import getLogger

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils.translation import override

from stockholm import Money

from joanie.core.enums import (
    ADMIN,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUSED,
    PRODUCT_TYPE_CERTIFICATE,
    PRODUCT_TYPE_CREDENTIAL,
)

logger = getLogger(__name__)


def prepare_context_data(
    order,
    installment_amount,
    credit_card_last_numbers,
    product_title,
    payment_refused: bool,
):
    """
    Prepare the context variables for the email when an installment has been paid
    or refused.
    """
    context_data = {
        "fullname": order.owner.name,
        "email": order.owner.email,
        "product_title": product_title,
        "installment_amount": Money(installment_amount),
        "product_price": Money(order.total),
        "credit_card_last_numbers": credit_card_last_numbers,
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
        order,
        installment_amount,
        order.credit_card.last_numbers,
        product_title,
        payment_refused=False,
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


def _prepare_withdrawal_context(order, title):
    """Prepare the common context variables for withdrawal-related emails."""
    product_title = order.product.safe_translation_getter(
        "title", language_code=order.owner.language
    )
    return {
        "title": title,
        "email": order.owner.email,
        "fullname": order.owner.name,
        "product_title": product_title,
        "dashboard_order_link": (
            settings.JOANIE_DASHBOARD_ORDER_LINK.replace(":orderId", str(order.id))
        ),
        "site": {
            "name": settings.JOANIE_CATALOG_NAME,
            "url": settings.JOANIE_CATALOG_BASE_URL,
        },
    }


def _prepare_withdrawal_recipients(order):
    """
    The withdrawal email should be sent to 3 recipients.
    Those recipients are : the buyer, the organization administrators, and the generic
    staff member mail.
    """
    recipients = [order.owner.email]

    support_email = None
    if order.product.type == PRODUCT_TYPE_CERTIFICATE:
        support_email = settings.JOANIE_EMAIL_SUPPORT_CERTIFICATE
    elif order.product.type == PRODUCT_TYPE_CREDENTIAL:
        support_email = settings.JOANIE_EMAIL_SUPPORT_CREDENTIAL
    if support_email:
        recipients.append(support_email)

    organization_emails = order.organization.accesses.filter(role=ADMIN).values_list(
        "user__email", flat=True
    )
    recipients.extend(list(organization_emails))

    return recipients


def _send_withdrawal_email(order, title, template_name):
    """Send a withdrawal-related mail to the order owner."""
    email_recipients = _prepare_withdrawal_recipients(order)
    for to_user_email in email_recipients:
        send(
            subject=title,
            template_vars=_prepare_withdrawal_context(order, title),
            template_name=template_name,
            to_user_email=to_user_email,
        )


def send_withdrawal_request(order):
    """
    Send a mail to the order owner confirming that their withdrawal request has been
    received and is pending manual review.
    """
    with override(order.owner.language):
        _send_withdrawal_email(
            order, _("Withdrawal request received"), "withdrawal_request"
        )


def send_withdrawal_confirmation(order):
    """
    Send a mail to the order owner confirming that their withdrawal has been
    confirmed and their order cancelled.
    """
    with override(order.owner.language):
        _send_withdrawal_email(
            order, _("Withdrawal confirmed"), "withdrawal_confirmation"
        )


def send_withdrawal_rejection(order):
    """
    Send a mail to the order owner informing them that their withdrawal request
    has been rejected and their order resumes its normal course.
    """
    with override(order.owner.language):
        _send_withdrawal_email(
            order, _("Withdrawal request rejected"), "withdrawal_rejection"
        )
