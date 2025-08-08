"""Batch Order Flows"""

import logging
from contextlib import suppress

from django.apps import apps

from viewflow import fsm

from joanie.core import enums

logger = logging.getLogger(__name__)


class BatchOrderFlow:
    """Batch order flow"""

    state = fsm.State(
        states=enums.BATCH_ORDER_STATE_CHOICES, default=enums.BATCH_ORDER_STATE_DRAFT
    )

    def __init__(self, instance):
        self.instance = instance

    @state.setter()
    def _set_order_state(self, value):
        self.instance.state = value

    @state.getter()
    def _get_order_state(self):
        return self.instance.state

    def _can_be_assigned(self):
        """
        A batch order can be assigned if it has an organization.
        """
        return self.instance.is_assigned

    @state.transition(
        source=enums.BATCH_ORDER_STATE_DRAFT,
        target=enums.BATCH_ORDER_STATE_ASSIGNED,
        conditions=[_can_be_assigned],
    )
    def assign(self):
        """
        Mark batch order as "assign" state.
        """

    def _can_be_quoted(self):
        """A batch order can be quoted if it is related to a quote"""
        return self.instance.has_quote

    @state.transition(
        source=enums.BATCH_ORDER_STATE_ASSIGNED,
        target=enums.BATCH_ORDER_STATE_QUOTED,
        conditions=[_can_be_quoted],
    )
    def quoted(self):
        "Mark batch order as quoted"

    def _can_be_state_to_sign(self):
        """
        When a batch order is paid through the purchase order, we should only allow to transition
        to `to_sign` state once the quote's purchase order is received. Otherwise, when the payment
        method is set with bank transfer or credit card, it can be set to `to_sign` once the quote
        has been signed by the organization.
        """
        return self.instance.can_be_signed

    @state.transition(
        source=[
            enums.BATCH_ORDER_STATE_ASSIGNED,
            enums.BATCH_ORDER_STATE_QUOTED,
        ],
        target=enums.BATCH_ORDER_STATE_TO_SIGN,
        conditions=[_can_be_state_to_sign],
    )
    def to_sign(self):
        """
        Mark batch order to "to_sign" state.
        """

    def _can_be_state_signing(self):
        """
        A batch order state can be set to signing when we validate that the buyer has signed.
        """
        return self.instance.is_signed_by_owner

    @state.transition(
        source=enums.BATCH_ORDER_STATE_TO_SIGN,
        target=enums.BATCH_ORDER_STATE_SIGNING,
        conditions=[_can_be_state_signing],
    )
    def signing(self):
        """
        Mark batch order as "signing" state.
        """

    def _can_be_state_pending(self):
        """
        A batch order can be set to pending for a payment because the contract has been
        signed or is in state failed payment.
        When the batch order uses a purchase order, it goes to completed directly after the
        contract is signed by the owner.
        """
        return self.instance.is_ready_for_payment

    @state.transition(
        source=[
            enums.BATCH_ORDER_STATE_SIGNING,
            enums.BATCH_ORDER_STATE_FAILED_PAYMENT,
        ],
        target=enums.BATCH_ORDER_STATE_PENDING,
        conditions=[_can_be_state_pending],
    )
    def pending(self):
        """
        Mark batch order instance as "pending" for payment.
        """

    @state.transition(
        source=enums.BATCH_ORDER_STATE_PENDING,
        target=enums.BATCH_ORDER_STATE_FAILED_PAYMENT,
    )
    def failed_payment(self):
        """
        Mark batch order instance as "failed_payment".
        """

    @state.transition(
        source=fsm.State.ANY,
        target=enums.BATCH_ORDER_STATE_CANCELED,
    )
    def cancel(self):
        """
        Mark batch order instance as "canceled".
        """

    def _can_be_state_completed(self):
        """
        A batch order can be in state completed because it has been fully paid
        """
        return self.instance.is_paid

    @state.transition(
        source=[
            enums.BATCH_ORDER_STATE_SIGNING,
            enums.BATCH_ORDER_STATE_PENDING,
        ],
        target=enums.BATCH_ORDER_STATE_COMPLETED,
        conditions=[_can_be_state_completed],
    )
    def completed(self):
        """Batch order is mark as complete because it's been paid"""

    def update(self):
        """
        Update the batch order state.
        """
        logger.debug("Transitioning batch order %s", self.instance.id)
        for transition in [
            self.assign,
            self.quoted,
            self.to_sign,
            self.signing,
            self.pending,
            self.completed,
        ]:
            with suppress(fsm.TransitionNotAllowed):
                logger.debug(
                    "  %s -> %s",
                    self.instance.state,
                    transition.label,
                )
                transition()
                logger.debug("  Done")
                return

    @state.on_success()
    def _post_transition_success(self, descriptor, source, target, **kwargs):  # pylint: disable=unused-argument
        """Post transition actions"""
        # When the batch order payment is successful, we should log the payment in Activity Log
        # When the batch order is related to a quote, the state goes from `signing`
        # to `completed` only if it's paid through purchase order
        ActivityLog = apps.get_model("core", "ActivityLog")  # pylint: disable=invalid-name
        if (
            source
            in [
                enums.BATCH_ORDER_STATE_SIGNING,
                enums.BATCH_ORDER_STATE_PENDING,
                enums.BATCH_ORDER_STATE_FAILED_PAYMENT,
            ]
            and target == enums.BATCH_ORDER_STATE_COMPLETED
        ):
            ActivityLog.create_payment_succeeded_activity_log(self.instance)
        # When the batch order payment has failed, we should log the payment in Activity Log
        if (
            source == enums.BATCH_ORDER_STATE_PENDING
            and target == enums.BATCH_ORDER_STATE_FAILED_PAYMENT
        ):
            ActivityLog.create_payment_failed_activity_log(self.instance)

        self.instance.save()
