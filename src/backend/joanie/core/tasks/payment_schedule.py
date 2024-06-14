"""Celery tasks for the payment schedule"""

from logging import getLogger

from django.utils import timezone

from joanie.celery_app import app
from joanie.core import enums
from joanie.core.models import Order
from joanie.payment import get_payment_backend

logger = getLogger(__name__)


@app.task
def process_today_installment(order_id):
    """
    Process the payment schedule for the order.
    """
    order = Order.objects.get(id=order_id)

    today = timezone.localdate()
    for installment in order.payment_schedule:
        if (
            installment["due_date"] <= today.isoformat()
            and installment["state"] == enums.PAYMENT_STATE_PENDING
        ):
            payment_backend = get_payment_backend()
            if not order.credit_card or not order.credit_card.token:
                order.set_installment_refused(installment["id"])
                continue

            payment_backend.create_zero_click_payment(
                order=order,
                credit_card_token=order.credit_card.token,
                installment=installment,
            )
