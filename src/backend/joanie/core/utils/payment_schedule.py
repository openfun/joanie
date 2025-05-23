"""
Payment schedule utility functions.
"""

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import override

from dateutil.relativedelta import relativedelta
from stockholm import Money, Number
from stockholm.exceptions import ConversionError

from joanie.core import enums
from joanie.core.exceptions import InvalidConversionError
from joanie.core.utils.emails import prepare_context_for_upcoming_installment, send
from joanie.payment import get_country_calendar
from joanie.payment.models import Invoice, Transaction

logger = logging.getLogger(__name__)


def _get_installments_percentages(total):
    """
    Return the payment installments percentages for the_ order.
    """
    percentages = None
    for limit, percentages in settings.JOANIE_PAYMENT_SCHEDULE_LIMITS.items():
        if total <= limit:
            return percentages
    return percentages


def _withdrawal_limit_date(signed_contract_date, course_start_date):
    """
    Return the withdrawal limit date for the order.

    On the withdrawal period of 14 days after the signing of the contract,
    it is counted as follows (article L 221-19 of the Consumer Code):

    - The day of the signing of the contract is not counted in the period;
      the countdown therefore begins the day after the contract is signed.

    - The period begins to run at the start of the first hour of the first
      day and ends at the expiration of the last hour of the last day of the period.

    - If the period expires on a Saturday, a Sunday or a public holiday or non-working day,
      it is extended until the next working day.

    The two first rules can be simplified with adding 16 days to the start date.
    So, the withdrawal limit date is the start date + 16 days.

    If the withdrawal limit date is after the course start date, the withdrawal limit
    date is set to the signed contract date to allow the user to starts the course
    immediately.
    """
    calendar = get_country_calendar()
    withdrawal_date = signed_contract_date + timedelta(
        days=settings.JOANIE_WITHDRAWAL_PERIOD_DAYS
    )

    if not calendar.is_working_day(withdrawal_date):
        withdrawal_date = calendar.add_working_days(
            withdrawal_date, 1, keep_datetime=True
        )

    return (
        withdrawal_date if withdrawal_date < course_start_date else signed_contract_date
    )


def _calculate_due_dates(
    withdrawal_date, course_start_date, course_end_date, installments_count
):
    """
    Calculate the due dates for the order.
    The first date is the withdrawal date
    Then the second one can not be before the course start date
    The last one can not be after the course end date
    """
    due_dates = [withdrawal_date]

    second_date = course_start_date
    if withdrawal_date > second_date:
        second_date = withdrawal_date + relativedelta(months=1)

    for i in range(installments_count - len(due_dates)):
        due_date = second_date + relativedelta(months=i)

        if due_date > course_end_date:
            # If due date is after end date, we should stop the loop, and add the end
            # date as the last due date
            due_dates.append(course_end_date)
            break
        due_dates.append(due_date)
    return due_dates


def _calculate_installments(total, due_dates, percentages):
    """
    Calculate the installments for the order.
    """
    total_amount = Money(total)
    installments = []
    for i, due_date in enumerate(due_dates):
        if i < len(due_dates) - 1:
            # All installments are using the setting percentages except the last one
            amount = round(total_amount * Number(percentages[i] / 100), 2)
        else:
            # Last installment is the remaining amount
            amount_sum = sum(installment["amount"] for installment in installments)
            amount = total_amount - amount_sum
        installments.append(
            {
                "id": uuid.uuid4(),
                "due_date": due_date,
                "amount": amount,
                "state": enums.PAYMENT_STATE_PENDING,
            }
        )
    return installments


def generate(total, beginning_contract_date, course_start_date, course_end_date):
    """
    Generate payment schedule for the order.
    """
    withdrawal_date = _withdrawal_limit_date(
        beginning_contract_date.date(), course_start_date.date()
    )
    percentages = _get_installments_percentages(total)
    due_dates = _calculate_due_dates(
        withdrawal_date,
        course_start_date.date(),
        course_end_date.date(),
        len(percentages),
    )
    installments = _calculate_installments(total, due_dates, percentages)

    return installments


def has_withdrawal_period(signed_contract_date, course_start_date):
    """
    If the withdrawal limit date is equal to the signed contract date, that means the
    payment schedule ignores the withdrawal period (because the course starts before
    the end of the withdrawal period).
    """

    limit_date = _withdrawal_limit_date(signed_contract_date, course_start_date)
    return limit_date != signed_contract_date


def is_installment_to_debit(installment):
    """
    Check if the installment is in a state to debit and has reached due date.
    """
    due_date = timezone.localdate()

    return (
        installment["state"] in enums.PAYMENT_STATES_TO_DEBIT
        and installment["due_date"] <= due_date
    )


def is_next_installment_to_debit(installment, due_date):
    """
    Check if the installment is in a state to debit and also
    if its due date will be equal to the parameter `due_date` passed.
    """

    return (
        installment["state"] in enums.PAYMENT_STATES_TO_DEBIT
        and installment["due_date"] == due_date
    )


def has_installments_to_debit(order):
    """
    Check if the order has any pending installments with reached due date.
    """

    return any(
        is_installment_to_debit(installment) for installment in order.payment_schedule
    )


def convert_date_str_to_date_object(date_str: str):
    """
    Converts the `date_str` string into a date object.
    """
    try:
        return date.fromisoformat(date_str)
    except ValueError as exception:
        raise InvalidConversionError(
            f"Invalid date format for date_str: {exception}."
        ) from exception


def convert_amount_str_to_money_object(amount_str: str):
    """
    Converts the `amount_str` string into a Money object.
    """
    try:
        return Money(amount_str)
    except ConversionError as exception:
        raise InvalidConversionError(
            f"Invalid format for amount: {exception} : '{amount_str}'."
        ) from exception


def send_mail_reminder_for_installment_debit(order, installment):
    """
    Prepare the context variables for the mail reminder when the next installment debit
    from the payment schedule will happen for the owner of the order.
    """
    with override(order.owner.language):
        product_title = order.product.safe_translation_getter(
            "title", language_code=order.owner.language
        )
        currency = settings.DEFAULT_CURRENCY
        days_until_debit = settings.JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS
        installment_amount = Money(installment["amount"])
        subject = _(
            f"{settings.JOANIE_CATALOG_NAME} - {product_title} - "
            f"An installment of {installment_amount} {currency} will be debited in "
            f"{days_until_debit} days."
        )

        send(
            subject=subject,
            template_vars=prepare_context_for_upcoming_installment(
                order, installment_amount, product_title, days_until_debit
            ),
            template_name="installment_reminder",
            to_user_email=order.owner.email,
        )


def has_installment_paid(order):
    """
    Check if at least 1 installment is paid in the payment schedule.
    """
    return not order.is_free and any(
        installment.get("state") == enums.PAYMENT_STATE_PAID
        for installment in order.payment_schedule
    )


def has_only_refunded_or_canceled_installments(order):
    """
    Check if installments are refunded or canceled  in the payment schedule.
    """
    return order.payment_schedule and all(
        installment.get("state")
        in (enums.PAYMENT_STATE_REFUNDED, enums.PAYMENT_STATE_CANCELED)
        for installment in order.payment_schedule
    )


def get_paid_transactions(order):
    """
    Return a transactions queryset that are made from the order on paid installments.
    """
    return (
        Transaction.objects.filter(
            invoice__order=order,
            invoice__parent__isnull=False,
        )
        .distinct()
        .order_by("created_on")
    )


def get_transaction_references_to_refund(order) -> dict:
    """
    Returns a dictionary containing transaction references as key that are eligible to be refunded
    and the concerned installment as value.
    """
    to_refund_items = {}
    used_installment_id = set()
    for transaction in get_paid_transactions(order):
        for installment in order.payment_schedule:
            if (
                installment["state"] == enums.PAYMENT_STATE_PAID
                and installment["amount"] == transaction.total
                and transaction.reference not in to_refund_items
                and installment["id"] not in used_installment_id
            ):
                to_refund_items[transaction.reference] = installment
                used_installment_id.add(installment["id"])
    return to_refund_items


def handle_refunded_transaction(invoice, amount: Decimal, refund_reference: str):
    """
    Handle the refund of an installment by creating a credit note, a transaction to reflect
    the cash movement.
    """
    credit_note = Invoice.objects.create(
        order=invoice.order,
        parent=invoice.order.main_invoice,
        total=-amount,
        recipient_address=invoice.recipient_address,
    )
    Transaction.objects.create(
        total=credit_note.total, invoice=credit_note, reference=refund_reference
    )
