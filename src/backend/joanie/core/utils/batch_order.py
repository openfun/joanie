"""
Util to cancel batch orders that are stuck in failed payment over the
tolerated time limit
"""

from joanie.core.models import BatchOrder


def cancel_batch_orders():
    """
    Cancel batch orders that are stuck in failed payment, and return the count of
    batch orders canceled.
    """
    canceled_batch_orders = 0
    found = BatchOrder.objects.get_stuck_failed_payment_batch_orders()
    for batch_order in found:
        batch_order.flow.cancel()
        batch_order.save()
        canceled_batch_orders += 1

    return canceled_batch_orders
