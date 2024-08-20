"""Celery tasks for the payment schedule"""

from logging import getLogger

from joanie.celery_app import app
from joanie.core.models import Order
from joanie.core.utils.payment_schedule import (
    is_installment_to_debit,
    send_mail_reminder_for_installment_debit,
)
from joanie.payment import get_payment_backend

logger = getLogger(__name__)


@app.task
def debit_pending_installment(order_id):
    """
    Process the payment schedule for the order. We debit all pending installments
    with a due date less than or equal to today.
    """
    order = Order.objects.get(id=order_id)

    for installment in order.payment_schedule:
        if is_installment_to_debit(installment):
            payment_backend = get_payment_backend()
            if not order.credit_card or not order.credit_card.token:
                order.set_installment_refused(installment["id"])
                continue

            payment_backend.create_zero_click_payment(
                order=order,
                credit_card_token=order.credit_card.token,
                installment=installment,
            )


@app.task
def send_mail_reminder_installment_debit_task(order_id, installment_id):
    """
    Task to send an email reminder to the order's owner about the next installment debit.
    """
    order = Order.objects.get(id=order_id)
    installment = next(
        (
            installment
            for installment in order.payment_schedule
            if installment["id"] == installment_id
        ),
        None,
    )
    send_mail_reminder_for_installment_debit(order, installment)
