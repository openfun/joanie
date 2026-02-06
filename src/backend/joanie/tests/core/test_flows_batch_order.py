"""
Test suite for Batch order flows.
"""

from django.utils import timezone

from viewflow import fsm

from joanie.core import enums, factories
from joanie.core.utils.batch_order import validate_success_payment
from joanie.payment.factories import (
    InvoiceFactory,
    TransactionFactory,
)
from joanie.tests.base import LoggingTestCase


class BatchOrderFlowsTestCase(LoggingTestCase):
    """Test suite for the Batch Order flow."""

    def test_flow_batch_order_draft(self):
        """
        When we create batch order and we don't call the init flow method, it
        should stay in draft state and not have an organization attach to it.
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_DRAFT)

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_DRAFT)
        self.assertIsNone(batch_order.organization)

    def test_flow_batch_assigned_requires_an_organization(self):
        """The batch order cannot be in assigned state if it does not have an organization"""
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_DRAFT)

        with self.assertRaises(fsm.TransitionNotAllowed):
            batch_order.flow.assign()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_DRAFT)

    def test_flow_batch_order_assigned(self):
        """When the batch order has an organization, it can be in state assigned."""
        batch_order = factories.BatchOrderFactory(organization=None)

        batch_order.organization = factories.OrganizationFactory()

        batch_order.flow.update()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_ASSIGNED)

    def test_flow_batch_order_quoted(self):
        """
        When the batch order is assigned and we generate a quote for it, it should transition
        to quoted state.
        """
        batch_order = factories.BatchOrderFactory(organization=None)
        batch_order.organization = factories.OrganizationFactory()
        batch_order.init_flow()
        batch_order.flow.update()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_QUOTED)

    def test_flow_batch_order_to_sign(self):
        """
        Depending the batch order's payment method, when it uses `bank_transfer` or `card_payment`,
        the state transitions from `quoted` to `to_sign` when calling `freeze_total`.
        Otherwise, when it uses `purchase_order`, it must first confirm the purchase order to
        transition to `to_sign`.
        """
        for payment_method, _ in enums.BATCH_ORDER_PAYMENT_METHOD_CHOICES:
            with self.subTest(payment_method=payment_method):
                batch_order = factories.BatchOrderFactory(
                    state=enums.BATCH_ORDER_STATE_QUOTED
                )

                batch_order.freeze_total("100.00")

                if batch_order.uses_purchase_order:
                    batch_order.quote.tag_has_purchase_order(
                        purchase_order_reference="test_reference"
                    )
                    self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)
                else:
                    self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)

    def test_flow_batch_order_signing(self):
        """
        When the contract has been signed by the buyer, the state of the batch order
        should transition to `pending` when the payment method is `bank_transfer`
        or `card_payment`. Otherwise, it transitions to `completed` with `purchase_order`.
        """
        for payment_method, _ in enums.BATCH_ORDER_PAYMENT_METHOD_CHOICES:
            with self.subTest(payment_method=payment_method):
                batch_order = factories.BatchOrderFactory(
                    state=enums.BATCH_ORDER_STATE_TO_SIGN, payment_method=payment_method
                )
                # The dummy backend signature marks the signature of the student
                batch_order.submit_for_signature()

                batch_order.flow.update()

                batch_order.refresh_from_db()

                if batch_order.uses_purchase_order:
                    self.assertEqual(
                        batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED
                    )
                else:
                    self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PENDING)

                self.assertIsNotNone(batch_order.contract.student_signed_on)
                self.assertIsNotNone(batch_order.contract.submitted_for_signature_on)

    def test_flow_batch_order_pending(self):
        """
        The batch order can be in state pending once the contract has been signed by at least
        the buyer.
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_SIGNING)

        batch_order.flow.update()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PENDING)

    def test_flow_batch_order_failed_payment(self):
        """
        The batch order can be in state failed payment if the payment went wrong.
        It can only happen when the payment method is `card_payment`.
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_PENDING)

        batch_order.flow.failed_payment()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_FAILED_PAYMENT)

    def test_flow_batch_order_failed_payment_with_bank_transfer(self):
        """
        A batch order cannot transition to failed payment if the payment method
        is by `bank_transfer`.
        """
        batch_order = factories.BatchOrderFactory(
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER
        )

        with self.assertRaises(fsm.TransitionNotAllowed) as context:
            batch_order.flow.failed_payment()

        self.assertTrue("Failed_Payment :: no transition" in str(context.exception))

    def test_flow_batch_order_failed_payment_with_purchase_order(self):
        """
        A batch order cannot transition to failed payment if the payment method is by
        `purchase_order`
        """
        batch_order = factories.BatchOrderFactory(
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER
        )

        with self.assertRaises(fsm.TransitionNotAllowed) as context:
            batch_order.flow.failed_payment()

        self.assertTrue("Failed_Payment :: no transition" in str(context.exception))

    def test_flow_batch_order_failed_payment_to_process_payment(self):
        """
        When the payment has failed for the batch order, it can go to `process_payment` state
        when the buyer attemps to fix the payment.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_FAILED_PAYMENT
        )

        batch_order.flow.process_payment()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PROCESS_PAYMENT)

    def test_flow_batch_order_completed(self):
        """
        When the batch order payment is made it can be in state completed.
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_PENDING)
        invoice = InvoiceFactory(
            batch_order=batch_order,
            parent=batch_order.main_invoice,
            total=0,
        )
        TransactionFactory(
            invoice=invoice,
            total=batch_order.total,
        )

        batch_order.flow.update()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)

    def test_flow_batch_order_cancel_orders(self):
        """
        We can cancel the order from any states.
        """

        for state, _ in enums.BATCH_ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state)
                batch_order.flow.cancel()

                self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_CANCELED)

    def test_flow_batch_order_process_payment(self):
        """
        We can mark a batch order into `process_payment` when it uses the `card_payment` payment
        method and is either `failed_payment`, `signing`, `pending` state.
        """
        for state, _ in enums.BATCH_ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state)
                if state in [
                    enums.BATCH_ORDER_STATE_PENDING,
                    enums.BATCH_ORDER_STATE_FAILED_PAYMENT,
                ]:
                    batch_order.flow.process_payment()
                    self.assertEqual(
                        batch_order.state, enums.BATCH_ORDER_STATE_PROCESS_PAYMENT
                    )
                else:
                    with self.assertRaises(fsm.TransitionNotAllowed):
                        batch_order.flow.process_payment()

    def test_flow_batch_order_assigned_to_completed_related_with_quote_and_purchase_order(
        self,
    ):
        """
        When a batch order uses the payment method `purchase_order`, once the quote has received
        the purchase order, and the buyer has signed the convention (contract), then the flow
        updates to `completed`. During that transition from `signing` to `completed` state,
        it generates the orders.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )
        # Simulate that the quote is signed by organization
        batch_order.freeze_total("100.00")
        # Simulate that we have received the purchase order
        batch_order.quote.tag_has_purchase_order(
            purchase_order_reference="test_reference"
        )

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)

        # Submit for signature the convention, should transition `signing``
        batch_order.submit_for_signature()

        batch_order.refresh_from_db()
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)
        self.assertTrue(batch_order.orders.exists())

    def test_flow_batch_order_assigned_to_completed_related_with_quote_and_bank_transfer(
        self,
    ):
        """
        When the batch order's payment method is by `bank_transfer`, it should transition in this
        order : from `assigned`, to `quoted`, to `to_sign`, `signing` to `pending`, and finally
        to `completed`.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
        )

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_QUOTED)

        # First the quote needs to be signed by the organization
        batch_order.quote.organization_signed_on = timezone.now()
        # Then, the quote is confirmed, and the organization sets the total
        batch_order.freeze_total("100.00")
        batch_order.flow.update()

        # It should transition to `to_sign` state
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)
        # Submit the contract to get signed, and make the buyer sign it.
        # When we submit for signature with the dummy backend signature, it triggers
        # the signature of the student and trigger the notification event.
        # The state becomes directly to `pending`.
        batch_order.submit_for_signature()

        batch_order.refresh_from_db()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PENDING)

        # Simulate that the bank transfer has been confirmed by the organization
        validate_success_payment(batch_order)

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)
        self.assertTrue(batch_order.orders.exists())
