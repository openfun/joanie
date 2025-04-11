"""Order flows."""

import logging
from contextlib import suppress

from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils import timezone

from sentry_sdk import capture_exception
from viewflow import fsm

from joanie.core import enums
from joanie.core.utils.payment_schedule import (
    has_installment_paid,
    has_installments_to_debit,
    has_only_refunded_or_canceled_installments,
    is_installment_to_debit,
)
from joanie.payment import get_payment_backend
from joanie.payment.backends.base import BasePaymentBackend

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

    def _can_be_state_to_own(self):
        """
        When an order has no owner and is attached to a batch order.
        """
        return self.instance.owner is None and self.instance.batch_order is not None

    @state.transition(
        source=enums.ORDER_STATE_ASSIGNED,
        target=enums.ORDER_STATE_TO_OWN,
        conditions=[_can_be_state_to_own],
    )
    def to_own(self):
        """Mark an order as `to_own`"""

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
        are completed, or if the order is already paid through a batch order.
        """
        if (
            self.instance.state == enums.ORDER_STATE_TO_OWN
            and self.instance.voucher.discount.rate == 1
        ):
            return self.instance.batch_order and self.instance.owner

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
            enums.ORDER_STATE_NO_PAYMENT,
            enums.ORDER_STATE_PENDING_PAYMENT,
            enums.ORDER_STATE_FAILED_PAYMENT,
            enums.ORDER_STATE_PENDING,
            enums.ORDER_STATE_SIGNING,
            enums.ORDER_STATE_TO_OWN,
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

    def _can_be_state_refunding(self):
        """
        An order state can be set to `refunding` if the order's state is 'canceled' exclusively.
        To be in state `refunding`, there should be at least one installment paid in the
        payment schedule of the order.
        """
        try:
            if self.instance.state != enums.ORDER_STATE_CANCELED:
                raise ValidationError("Cannot refund an order not canceled.")

            if not has_installment_paid(self.instance):
                raise ValidationError(
                    "Cannot refund an order without paid installments in payment schedule."
                )
            return True
        except ValidationError as error:
            capture_exception(error)
            return False

    @state.transition(
        source=enums.ORDER_STATE_CANCELED,
        target=enums.ORDER_STATE_REFUNDING,
        conditions=[_can_be_state_refunding],
    )
    def refunding(self):
        """
        Mark an order as in "refunding".
        """

    def _can_be_state_refunded(self):
        """
        The order's state should be in "refunding" and there is no more installment
        in the payment schedule marked as "paid".
        """
        return (
            self.instance.state == enums.ORDER_STATE_REFUNDING
            and has_only_refunded_or_canceled_installments(self.instance)
        )

    @state.transition(
        source=enums.ORDER_STATE_REFUNDING,
        target=enums.ORDER_STATE_REFUNDED,
        conditions=[_can_be_state_refunded],
    )
    def refunded(self):
        """Mark an order as "refunded" """

    def update(self):
        """
        Update the order state.
        """
        logger.debug("Transitioning order %s", self.instance.id)
        for transition in [
            self.to_own,
            self.complete,
            self.to_sign,
            self.signing,
            self.to_save_payment_method,
            self.pending,
            self.pending_payment,
            self.no_payment,
            self.failed_payment,
            self.refunded,
            self.to_own,
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
        # When an order's subscription is confirmed, we send an email to the user about the
        # confirmation
        if (
            source
            in [enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD, enums.ORDER_STATE_SIGNING]
            and target == enums.ORDER_STATE_PENDING
        ):
            # pylint: disable=protected-access
            # ruff : noqa : SLF001
            BasePaymentBackend._send_mail_subscription_success(order=self.instance)

        if (
            not source == enums.ORDER_STATE_TO_OWN
            and not self.instance.payment_schedule
            and not self.instance.is_free
            and target in [enums.ORDER_STATE_PENDING, enums.ORDER_STATE_COMPLETED]
        ):
            self.instance.generate_schedule()

        # When we generate the payment schedule and if the course has already started,
        # the 1st installment due date of the order's payment schedule will be set to the current
        # day. Since we only debit the next night through a cronjob, we need be able to make the
        # user pay to have access to his course, and avoid that the has to wait the next
        # day to start it.
        if (
            source == enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD
            and target == enums.ORDER_STATE_PENDING
            and has_installments_to_debit(self.instance)
            and self.instance.credit_card
            and self.instance.credit_card.token
        ):
            installment = next(
                (
                    installment
                    for installment in self.instance.payment_schedule
                    if is_installment_to_debit(installment)
                ),
            )
            payment_backend = get_payment_backend()
            payment_backend.create_zero_click_payment(
                order=self.instance,
                credit_card_token=self.instance.credit_card.token,
                installment=installment,
            )

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
            source
            in [
                enums.ORDER_STATE_PENDING,
                enums.ORDER_STATE_NO_PAYMENT,
                enums.ORDER_STATE_TO_OWN,
            ]
            and target
            in [enums.ORDER_STATE_PENDING_PAYMENT, enums.ORDER_STATE_COMPLETED]
        ):
            try:
                # ruff : noqa : BLE001
                # pylint: disable=broad-exception-caught
                self.instance.enroll_user_to_course_run()
            except Exception as error:
                capture_exception(error)

        if target in [enums.ORDER_STATE_CANCELED, enums.ORDER_STATE_REFUNDED]:
            self.instance.cancel_remaining_installments()

        if target == enums.ORDER_STATE_CANCELED:
            self.instance.unenroll_user_from_course_runs()

        if self.instance.credit_card and target in [
            enums.ORDER_STATE_COMPLETED,
            enums.ORDER_STATE_CANCELED,
        ]:
            # delete card
            credit_card = self.instance.credit_card
            self.instance.credit_card = None
            self.instance.save()
            if not credit_card.orders.exists():
                credit_card.delete()

        # Reset course product relation cache if its representation is impacted by changes
        # on related orders
        # e.g. number of remaining seats when an order group is used
        # see test_api_course_product_relation_read_detail_with_order_groups_cache
        if self.instance.order_groups.exists():
            course_id = (
                self.instance.course_id or self.instance.enrollment.course_run.course_id
            )
            CourseProductRelation = apps.get_model("core", "CourseProductRelation")  # pylint: disable=invalid-name
            CourseProductRelation.objects.filter(
                product_id=self.instance.product_id, course_id=course_id
            ).update(updated_on=timezone.now())
