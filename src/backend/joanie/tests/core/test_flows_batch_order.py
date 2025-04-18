"""
Test suite for Batch order flows.
"""

from django.utils import timezone

from viewflow import fsm

from joanie.core import enums, factories
from joanie.signature.backends import get_signature_backend
from joanie.tests.base import LoggingTestCase


class BatchOrderFlowsTestCase(LoggingTestCase):
    """Test suite for the Batch Order flow."""

    def create_batch_order_with_signed_contract(self, state):
        """
        Create a batch order where the organization is already assigned, and the contract
        is signed by the buyer.
        """
        return factories.BatchOrderFactory(
            contract=factories.ContractFactory(
                submitted_for_signature_on=timezone.now(),
                student_signed_on=timezone.now(),
                organization_signed_on=None,
                context="context",
                definition_checksum="1234",
                signature_backend_reference="wfl_test_id",
            ),
            state=state,
        )

    def test_flow_batch_order_draft(self):
        """
        When we create batch order and we don't call the init flow method, it
        should stay in draft state and not have an organization attach to it.
        """
        batch_order = factories.BatchOrderFactory(organization=None)

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_DRAFT)
        self.assertIsNone(batch_order.organization)

    def test_flow_batch_assigned_requires_an_organization(self):
        """The batch order cannot be in assigned state if it does not have an organization"""
        batch_order = factories.BatchOrderFactory(organization=None)

        with self.assertRaises(fsm.TransitionNotAllowed):
            batch_order.flow.assign()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_DRAFT)

    def test_flow_batch_order_assigned(self):
        """When the batch order has an organization, it can be in state assigned."""
        batch_order = factories.BatchOrderFactory(organization=None)

        batch_order.organization = factories.OrganizationFactory()

        batch_order.flow.update()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_ASSIGNED)

    def test_flow_batch_order_to_sign_because_submit_for_signature(self):
        """
        When we submit to signature the batch order contract, it should change the state
        to `to_sign`. It means that the contract is submitted and requires a signature
        from the buyer.
        """
        batch_order = factories.BatchOrderFactory(
            organization=factories.OrganizationFactory()
        )
        batch_order.init_flow()

        batch_order.submit_for_signature(user=batch_order.owner)

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)

    def test_flow_batch_order_signing(self):
        """
        When the contract has been signed by the buyer, the state of the batch order
        should transition to signing.
        """
        batch_order = factories.BatchOrderFactory(
            organization=factories.OrganizationFactory()
        )
        batch_order.init_flow()
        batch_order.submit_for_signature(user=batch_order.owner)

        # Trigger the event of the buyer signing the contract
        signature_backend = get_signature_backend()
        signature_backend.confirm_signature(
            reference=batch_order.contract.signature_backend_reference
        )

        batch_order.contract.refresh_from_db()
        batch_order.flow.signing()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_SIGNING)
        self.assertIsNotNone(batch_order.contract.student_signed_on)
        self.assertIsNotNone(batch_order.contract.submitted_for_signature_on)

    def test_flow_batch_order_pending(self):
        """
        The batch order can be in state pending once the contract has been signed by at least
        the buyer.
        """
        batch_order = self.create_batch_order_with_signed_contract(
            state=enums.BATCH_ORDER_STATE_SIGNING
        )

        batch_order.flow.update()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PENDING)

    def test_flow_batch_order_failed_payment(self):
        """
        The batch order can be in state failed payment if the payment went wrong.
        """
        batch_order = self.create_batch_order_with_signed_contract(
            state=enums.BATCH_ORDER_STATE_PENDING
        )

        batch_order.flow.failed_payment()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_FAILED_PAYMENT)

    def test_flow_batch_order_failed_payment_to_pending(self):
        """
        When the payment has failed for the batch order, it can go back into pending state
        when the buyer attemps to fix the payment.
        """
        batch_order = self.create_batch_order_with_signed_contract(
            state=enums.BATCH_ORDER_STATE_FAILED_PAYMENT
        )

        batch_order.flow.pending()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PENDING)

    def test_flow_batch_order_completed(self):
        """
        When the batch order payment is made it can be in state completed.
        """
        batch_order = self.create_batch_order_with_signed_contract(
            state=enums.BATCH_ORDER_STATE_PENDING
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
