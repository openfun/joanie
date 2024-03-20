"""
Payment schedule utility functions.
"""

import logging
from datetime import timedelta

from django.conf import settings

from dateutil.relativedelta import relativedelta
from stockholm import Money, Number
from workalendar.europe import France

from joanie.core import enums

logger = logging.getLogger(__name__)


def _get_installments_percentages(total):
    """
    Return the payment installments percentages for the order.
    """
    percentages = None
    for limit, percentages in settings.PAYMENT_SCHEDULE_LIMITS.items():
        if total <= limit:
            return percentages
    return percentages


def _retraction_date(start_date):
    """
    Return the retraction date for the order.
    """
    calendar = France()
    retraction_date = start_date.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=16)
    if not calendar.is_working_day(retraction_date):
        return calendar.add_working_days(retraction_date, 1, keep_datetime=True)
    return retraction_date


def _calculate_due_dates(start_date, end_date, percentages_count):
    """
    Calculate the due dates for the order.
    """
    due_dates = []
    for i in range(percentages_count):
        due_date = start_date + relativedelta(months=i)
        if due_date > end_date:
            # If due date is after end date, we should stop the loop, and add the end
            # date as the last due date
            due_dates.append(end_date)
            break
        due_dates.append(min(due_date, end_date))
    return due_dates


def _calculate_installments(total, due_dates, percentages):
    """
    Calculate the installments for the order.
    """
    total_amount = Money(total, settings.DEFAULT_CURRENCY)
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
                "due_date": due_date,
                "amount": amount,
                "state": enums.PAYMENT_STATE_PENDING,
            }
        )
    return installments


def generate(total, start_date, end_date):
    """
    Generate payment schedule for the order.
    """
    retraction_date = _retraction_date(start_date)
    percentages = _get_installments_percentages(total)
    due_dates = _calculate_due_dates(retraction_date, end_date, len(percentages))
    installments = _calculate_installments(total, due_dates, percentages)

    return installments
