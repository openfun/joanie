"""Test suite for utils order methods"""

from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories, models
from joanie.core.utils.batch_order import cancel_batch_orders


class UtilsBatchOrderTestCase(TestCase):
    """Test suite for utils batch order methods"""

    def test_utils_batch_order_cancel_when_state_is_failed_payment(self):
        """
        Calling the method cancel batch order should only be able to cancel order
        that are in `failed_payment` state.
        """
        for state, _ in enums.BATCH_ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state)
                beyond_tolerated_time = batch_order.updated_on + timedelta(
                    seconds=settings.JOANIE_BATCH_ORDER_FIX_PAYMENT_DELAY_LIMIT
                )
                with mock.patch(
                    "django.utils.timezone.now", return_value=beyond_tolerated_time
                ):
                    canceled_batch_orders_count = cancel_batch_orders()
                    batch_order.refresh_from_db()
                    if state == enums.BATCH_ORDER_STATE_FAILED_PAYMENT:
                        self.assertEqual(
                            batch_order.state, enums.BATCH_ORDER_STATE_CANCELED
                        )
                        self.assertEqual(canceled_batch_orders_count, 1)
                    else:
                        self.assertEqual(batch_order.state, state)
                        self.assertEqual(canceled_batch_orders_count, 0)
