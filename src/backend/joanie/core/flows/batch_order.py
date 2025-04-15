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
        return self.instance.organization is not None

    @state.transition(
        source=enums.BATCH_ORDER_STATE_DRAFT,
        target=enums.BATCH_ORDER_STATE_ASSIGNED,
        conditions=[_can_be_assigned],
    )
    def assign(self):
        """
        Mark batch order as "assign" state.
        """

    def _can_be_state_to_sign(self):
        """
        A batch order state can be set to `to_sign` if it has an unsigned contract but
        is submitted at the signature provider.
        """
        return (
            self.instance.contract.student_signed_on is None
            and self.instance.contract.submitted_for_signature_on is not None
        )

    @state.transition(
        source=enums.BATCH_ORDER_STATE_ASSIGNED,
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
        return (
            self.instance.contract.submitted_for_signature_on
            and self.instance.contract.student_signed_on
        )

    @state.transition(
        source=enums.BATCH_ORDER_STATE_TO_SIGN,
        target=enums.BATCH_ORDER_STATE_SIGNING,
        conditions=[_can_be_state_signing],
    )
    def signing(self):
        """
        Mark batch order as "signing" state.
        """

    @state.transition(
        source=[
            enums.BATCH_ORDER_STATE_SIGNING,
            enums.BATCH_ORDER_STATE_FAILED_PAYMENT,
        ],
        target=enums.BATCH_ORDER_STATE_PENDING,
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

    @state.transition(
        source=enums.BATCH_ORDER_STATE_PENDING,
        target=enums.BATCH_ORDER_STATE_COMPLETED,
    )
    def completed(self):
        """Batch order is mark as complete because it's been paid"""

    def update(self):
        """
        Update the batch order state.
        """
        logger.debug("Transitioning order %s", self.instance.id)
        for transition in [
            self.assign,
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
        ActivityLog = apps.get_model("core", "ActivityLog")  # pylint: disable=invalid-name
        if (
            source
            in [enums.BATCH_ORDER_STATE_PENDING, enums.BATCH_ORDER_STATE_FAILED_PAYMENT]
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
