"""Celery tasks for the payment schedule"""

from logging import getLogger

from django.apps import apps

from joanie.celery_app import app
from joanie.core.enums import PAYMENT_STATE_ERROR, PAYMENT_STATE_REFUSED
from joanie.core.utils.payment_schedule import (
    is_installment_to_debit,
    send_mail_reminder_for_installment_debit,
)
from joanie.payment import get_payment_backend
from joanie.payment.exceptions import PaymentProviderAPIException

logger = getLogger(__name__)


@app.task
def debit_pending_installment(order_id):
    """
    Process the payment schedule for the order. We debit all installments in a state
    to be debited with a due date less than or equal to today.
    """
    Order = apps.get_model("core", "Order")  # pylint: disable=invalid-name
    order = Order.objects.get(id=order_id)

    for installment in order.payment_schedule:
        if is_installment_to_debit(installment):
            payment_backend = get_payment_backend()
            if not order.credit_card or not order.credit_card.token:
                order.set_installment_refused(installment["id"])
                continue

            transition_to_refused_state = None
            if installment["state"] == PAYMENT_STATE_ERROR:
                order.set_installment_refused(installment["id"])
                transition_to_refused_state = installment["state"]

            if payment_backend.is_already_paid(order, installment):
                logger.info(
                    "Installment %s for order %s already paid.",
                    installment["id"],
                    order.id,
                )
                continue

            try:
                payment_backend.create_zero_click_payment(
                    order=order,
                    credit_card_token=order.credit_card.token,
                    installment=installment,
                )
            except PaymentProviderAPIException:
                logger.exception(
                    "Error processing installment %s for order %s.",
                    installment["id"],
                    order.id,
                )
                if not transition_to_refused_state == PAYMENT_STATE_REFUSED:
                    order.set_installment_error(installment["id"])
                # Leave in refused state the installment that failed second time
                # to let the frontend consumer solve his payment with another credit
                # card
                continue


@app.task
def send_mail_reminder_installment_debit_task(order_id, installment_id):
    """
    Task to send an email reminder to the order's owner about the next installment debit.
    """
    Order = apps.get_model("core", "Order")  # pylint: disable=invalid-name
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
