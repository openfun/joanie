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

    def test_flow_batch_order_to_sign_because_submit_for_signature(self):
        """
        Before submitting to signature the contract, we should first mark the quote
        as signed by the organization. Only then, when submitting to signature the contract,
        it should change the state to `to_sign`.
        It means that the contract is submitted and requests a signature from the buyer.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED
        )
        batch_order.quote.organization_signed_on = timezone.now()

        batch_order.submit_for_signature(user=batch_order.owner)

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)

    def test_flow_batch_order_signing(self):
        """
        When the contract has been signed by the buyer, the state of the batch order
        should transition to signing.
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_TO_SIGN)
        batch_order.contract.student_signed_on = timezone.now()

        batch_order.flow.update()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_SIGNING)
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
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_PENDING)

        batch_order.flow.failed_payment()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_FAILED_PAYMENT)

    def test_flow_batch_order_failed_payment_to_pending(self):
        """
        When the payment has failed for the batch order, it can go back into pending state
        when the buyer attemps to fix the payment.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_FAILED_PAYMENT
        )

        batch_order.flow.update()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PENDING)

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

    def test_flow_batch_order_assigned_to_complete_related_with_quote_and_purchase_order(
        self,
    ):
        """
        When the quote related to the batch order has received the purchase order,
        and the buyer has signed the convention (contract), then the flow can update to
        `completed`. That way, we can generate the orders for a batch order related to a quote.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_QUOTED)

        batch_order.quote.organization_signed_on = timezone.now()
        batch_order.freeze_total("100.00")

        # Simulate that we have received the purchase order
        batch_order.quote.has_purchase_order = True
        batch_order.quote.save()

        # Submit for signature the convention, should transition `to_sign``
        batch_order.submit_for_signature(batch_order.owner)

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)

        # Simulate that the buyer has signed the convention
        batch_order.contract.student_signed_on = timezone.now()
        batch_order.flow.update()

        # Should transition to `signing`
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_SIGNING)

        # Should transition to `completed`, because it is paid through quote purchase order
        batch_order.flow.update()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)
        self.assertTrue(batch_order.orders.exists())

    def test_flow_batch_order_assigned_to_complete_related_with_quote_and_bank_transfer(
        self,
    ):
        """
        When the batch order's payment method is by bank transfer, it should transition in this
        order : assigned, to quoted, to sign, signing, pending, completed.
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
        # Submit the contract to get signed, and make the buyer sign it
        batch_order.submit_for_signature(batch_order.owner)
        batch_order.contract.student_signed_on = timezone.now()
        batch_order.flow.update()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_SIGNING)

        batch_order.flow.update()

        # Should transition to pending
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PENDING)

        # Simulate that the bank transfer has been confirmed by the organization
        validate_success_payment(batch_order)

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)
        self.assertTrue(batch_order.orders.exists())
