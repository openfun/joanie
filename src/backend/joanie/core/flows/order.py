"""Order flows."""

import logging
from contextlib import suppress

from django.apps import apps
from django.utils import timezone

from sentry_sdk import capture_exception
from viewflow import fsm

from joanie.core import enums

logger = logging.getLogger(__name__)


class OrderFlow:
    """Order flow"""

    state = fsm.State(states=enums.ORDER_STATE_CHOICES, default=enums.ORDER_STATE_DRAFT)

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
        An order can be assigned if it has an organization.
        """
        return self.instance.organization is not None

    @state.transition(
        source=enums.ORDER_STATE_DRAFT,
        target=enums.ORDER_STATE_ASSIGNED,
        conditions=[_can_be_assigned],
    )
    def assign(self):
        """
        Transition order to assigned state.
        """

    def _can_be_state_to_save_payment_method(self):
        """
        An order state can be set to_save_payment_method if the order is not free
        has no payment method and no contract to sign.
        """
        return (
            not self.instance.is_free
            and not self.instance.has_payment_method
            and not self.instance.has_unsigned_contract
        )

    @state.transition(
        source=[
            enums.ORDER_STATE_ASSIGNED,
            enums.ORDER_STATE_SIGNING,
            enums.ORDER_STATE_PENDING,
        ],
        target=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
        conditions=[_can_be_state_to_save_payment_method],
    )
    def to_save_payment_method(self):
        """
        Transition order to to_save_payment_method state.
        """

    def _can_be_state_to_sign(self):
        """
        An order state can be set to to_sign if the order has an unsigned contract.
        """
        return (
            self.instance.has_unsigned_contract
            and not self.instance.has_submitted_contract
        )

    @state.transition(
        source=[enums.ORDER_STATE_ASSIGNED, enums.ORDER_STATE_SIGNING],
        target=enums.ORDER_STATE_TO_SIGN,
        conditions=[_can_be_state_to_sign],
    )
    def to_sign(self):
        """
        Transition order to to_sign state.
        """

    def _can_be_state_signing(self):
        """
        An order state can be set to signing if
        we are waiting for the signature provider to validate the student's signature.
        """
        return (
            self.instance.contract.submitted_for_signature_on
            and not self.instance.contract.student_signed_on
        )

    @state.transition(
        source=enums.ORDER_STATE_TO_SIGN,
        target=enums.ORDER_STATE_SIGNING,
        conditions=[_can_be_state_signing],
    )
    def signing(self):
        """
        Transition order to signing state.
        """

    def _can_be_state_pending(self):
        """
        An order state can be set to pending if the order is not free
        and has a payment method and no contract to sign.
        """
        return (
            self.instance.is_free or self.instance.has_payment_method
        ) and not self.instance.has_unsigned_contract

    @state.transition(
        source=[
            enums.ORDER_STATE_ASSIGNED,
            enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            enums.ORDER_STATE_SIGNING,
        ],
        target=enums.ORDER_STATE_PENDING,
        conditions=[_can_be_state_pending],
    )
    def pending(self):
        """
        Transition order to pending state.
        """

    @state.transition(
        source=fsm.State.ANY,
        target=enums.ORDER_STATE_CANCELED,
    )
    def cancel(self):
        """
        Mark order instance as "canceled".
        """

    def _can_be_state_completed(self):
        """
        An order state can be set to completed if all installments
        are completed.
        """
        fully_paid = self.instance.is_free
        if not fully_paid and self.instance.payment_schedule:
            fully_paid = all(
                installment.get("state") in [enums.PAYMENT_STATE_PAID]
                for installment in self.instance.payment_schedule
            )
        return fully_paid and not self.instance.has_unsigned_contract

    @state.transition(
        source=[
            enums.ORDER_STATE_ASSIGNED,
            enums.ORDER_STATE_PENDING_PAYMENT,
            enums.ORDER_STATE_FAILED_PAYMENT,
            enums.ORDER_STATE_PENDING,
            enums.ORDER_STATE_SIGNING,
        ],
        target=enums.ORDER_STATE_COMPLETED,
        conditions=[_can_be_state_completed],
    )
    def complete(self):
        """
        Complete the order.
        """

    def _can_be_state_pending_payment(self):
        """
        An order state can be set to pending_payment if the first installment
        is paid and all others are not refused.
        """

        [first_installment_state, *other_installments_states] = [
            installment.get("state") for installment in self.instance.payment_schedule
        ]

        return first_installment_state == enums.PAYMENT_STATE_PAID and not any(
            state == enums.PAYMENT_STATE_REFUSED for state in other_installments_states
        )

    @state.transition(
        source=[
            enums.ORDER_STATE_PENDING_PAYMENT,
            enums.ORDER_STATE_FAILED_PAYMENT,
            enums.ORDER_STATE_NO_PAYMENT,
            enums.ORDER_STATE_PENDING,
        ],
        target=enums.ORDER_STATE_PENDING_PAYMENT,
        conditions=[_can_be_state_pending_payment],
    )
    def pending_payment(self):
        """
        Mark order instance as "pending_payment".
        """

    def _can_be_state_no_payment(self):
        """
        An order state can be set to no_payment if the first installment is refused.
        """
        return self.instance.payment_schedule[0].get("state") in [
            enums.PAYMENT_STATE_REFUSED
        ]

    @state.transition(
        source=enums.ORDER_STATE_PENDING,
        target=enums.ORDER_STATE_NO_PAYMENT,
        conditions=[_can_be_state_no_payment],
    )
    def no_payment(self):
        """
        Mark order instance as "no_payment".
        """

    def _can_be_state_failed_payment(self):
        """
        An order state can be set to failed_payment if any installment except the first
        is refused.
        """
        return any(
            installment.get("state") in [enums.PAYMENT_STATE_REFUSED]
            for installment in self.instance.payment_schedule[1:]
        )

    @state.transition(
        source=enums.ORDER_STATE_PENDING_PAYMENT,
        target=enums.ORDER_STATE_FAILED_PAYMENT,
        conditions=[_can_be_state_failed_payment],
    )
    def failed_payment(self):
        """
        Mark order instance as "failed_payment".
        """

    def update(self):
        """
        Update the order state.
        """
        logger.debug("Transitioning order %s", self.instance.id)
        for transition in [
            self.complete,
            self.to_sign,
            self.signing,
            self.to_save_payment_method,
            self.pending,
            self.pending_payment,
            self.no_payment,
            self.failed_payment,
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
        self.instance.save()

        # When an order is completed, if the user was previously enrolled for free in any of the
        # course runs targeted by the purchased product, we should change their enrollment mode on
        # these course runs to "verified".
        if (
            source
            in [
                enums.ORDER_STATE_ASSIGNED,
                enums.ORDER_STATE_PENDING,
                enums.ORDER_STATE_NO_PAYMENT,
            ]
            and target
            in [enums.ORDER_STATE_PENDING_PAYMENT, enums.ORDER_STATE_COMPLETED]
        ) or target == enums.ORDER_STATE_CANCELED:
            for enrollment in self.instance.get_target_enrollments(
                is_active=True
            ).select_related("course_run", "user"):
                enrollment.set()

        # Enroll user if the order is assigned, pending or no payment and the target is
        # completed or pending payment.
        # assign -> completed : free product without contract
        # pending -> pending_payment : first installment paid
        # no_payment -> pending_payment : first installment paid
        # pending -> completed : fully paid order
        # no_payment -> completed : fully paid order
        if (
            source == enums.ORDER_STATE_ASSIGNED
            and target == enums.ORDER_STATE_COMPLETED
        ) or (
            source in [enums.ORDER_STATE_PENDING, enums.ORDER_STATE_NO_PAYMENT]
            and target
            in [enums.ORDER_STATE_PENDING_PAYMENT, enums.ORDER_STATE_COMPLETED]
        ):
            try:
                # ruff : noqa : BLE001
                # pylint: disable=broad-exception-caught
                self.instance.enroll_user_to_course_run()
            except Exception as error:
                capture_exception(error)

        if target == enums.ORDER_STATE_CANCELED:
            self.instance.unenroll_user_from_course_runs()

        if order_enrollment := self.instance.enrollment:
            # Trigger LMS synchronization for source enrollment to update mode
            # Make sure it is saved in case the state is modified e.g in case of synchronization
            # failure
            order_enrollment.set()

        # Reset course product relation cache if its representation is impacted by changes
        # on related orders
        # e.g. number of remaining seats when an order group is used
        # see test_api_course_product_relation_read_detail_with_order_groups_cache
        if self.instance.order_group:
            course_id = (
                self.instance.course_id or self.instance.enrollment.course_run.course_id
            )
            CourseProductRelation = apps.get_model("core", "CourseProductRelation")  # pylint: disable=invalid-name
            CourseProductRelation.objects.filter(
                product_id=self.instance.product_id, course_id=course_id
            ).update(updated_on=timezone.now())
