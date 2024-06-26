"""Order flows."""

from django.apps import apps
from django.utils import timezone

from sentry_sdk import capture_exception
from viewflow import fsm

from joanie.core import enums
from joanie.payment import get_payment_backend


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

    def _can_be_state_submitted(self):
        """
        An order can be submitted if the order has a course, an organization,
        an owner, and a product
        """
        return (
            (self.instance.course is not None or self.instance.enrollment is not None)
            and self.instance.organization is not None
            and self.instance.owner is not None
            and self.instance.product is not None
        )

    def _can_be_state_validated(self):
        """
        An order can be validated if the product is free or if it
        has invoices.
        """
        return (
            self.instance.total == enums.MIN_ORDER_TOTAL_AMOUNT
            or self.instance.invoices.count() > 0
        )

    @state.transition(
        source=[enums.ORDER_STATE_DRAFT, enums.ORDER_STATE_PENDING],
        target=enums.ORDER_STATE_SUBMITTED,
        conditions=[_can_be_state_submitted],
    )
    def submit(self, billing_address=None, credit_card_id=None):
        """
        Transition order to submitted state.
        Create a payment if the product is fee
        """
        CreditCard = apps.get_model("payment", "CreditCard")  # pylint: disable=invalid-name
        payment_backend = get_payment_backend()
        if credit_card_id:
            try:
                credit_card = CreditCard.objects.get_card_for_owner(
                    pk=credit_card_id,
                    username=self.instance.owner.username,
                )
                return payment_backend.create_one_click_payment(
                    order=self.instance,
                    billing_address=billing_address,
                    credit_card_token=credit_card.token,
                )
            except (CreditCard.DoesNotExist, NotImplementedError):
                pass
        payment_info = payment_backend.create_payment(
            order=self.instance, billing_address=billing_address
        )

        return payment_info

    @state.transition(
        source=[
            enums.ORDER_STATE_DRAFT,
            enums.ORDER_STATE_SUBMITTED,
        ],
        target=enums.ORDER_STATE_VALIDATED,
        conditions=[_can_be_state_validated],
    )
    def validate(self):
        """
        Transition order to validated state.
        """

    @state.transition(
        source=fsm.State.ANY,
        target=enums.ORDER_STATE_CANCELED,
    )
    def cancel(self):
        """
        Mark order instance as "canceled".
        """

    @state.transition(
        source=[enums.ORDER_STATE_SUBMITTED, enums.ORDER_STATE_VALIDATED],
        target=enums.ORDER_STATE_PENDING,
    )
    def pending(self, payment_id=None):
        """
        Mark order instance as "pending" and abort the related
        payment if there is one
        """
        if payment_id:
            payment_backend = get_payment_backend()
            payment_backend.abort_payment(payment_id)

    def _can_be_state_pending_payment(self):
        """
        An order state can be set to pending_payment if no installment
        is refused.
        """
        return any(
            installment.get("state") not in [enums.PAYMENT_STATE_REFUSED]
            for installment in self.instance.payment_schedule
        )

    def _can_be_state_completed(self):
        """
        An order state can be set to completed if all installments
        are completed.
        """
        return all(
            installment.get("state") in [enums.PAYMENT_STATE_PAID]
            for installment in self.instance.payment_schedule
        )

    def _can_be_state_no_payment(self):
        """
        An order state can be set to no_payment if the first installment is refused.
        """
        return self.instance.payment_schedule[0].get("state") in [
            enums.PAYMENT_STATE_REFUSED
        ]

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
        source=[
            enums.ORDER_STATE_PENDING_PAYMENT,
            enums.ORDER_STATE_FAILED_PAYMENT,
            enums.ORDER_STATE_PENDING,
        ],
        target=enums.ORDER_STATE_COMPLETED,
        conditions=[_can_be_state_completed],
    )
    def complete(self):
        """
        Complete the order.
        """

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

    @state.transition(
        source=enums.ORDER_STATE_PENDING,
        target=enums.ORDER_STATE_NO_PAYMENT,
        conditions=[_can_be_state_no_payment],
    )
    def no_payment(self):
        """
        Mark order instance as "no_payment".
        """

    @state.transition(
        source=enums.ORDER_STATE_PENDING_PAYMENT,
        target=enums.ORDER_STATE_FAILED_PAYMENT,
        conditions=[_can_be_state_failed_payment],
    )
    def failed_payment(self):
        """
        Mark order instance as "failed_payment".
        """

    @state.on_success()
    def _post_transition_success(self, descriptor, source, target):  # pylint: disable=unused-argument
        """Post transition actions"""
        self.instance.save()

        # When an order is validated, if the user was previously enrolled for free in any of the
        # course runs targeted by the purchased product, we should change their enrollment mode on
        # these course runs to "verified".
        if target in [enums.ORDER_STATE_VALIDATED, enums.ORDER_STATE_CANCELED]:
            for enrollment in self.instance.get_target_enrollments(
                is_active=True
            ).select_related("course_run", "user"):
                enrollment.set()

        # Only enroll user if the product has no contract to sign, otherwise we should wait
        # for the contract to be signed before enrolling the user.
        if (
            target == enums.ORDER_STATE_VALIDATED
            and self.instance.product.contract_definition is None
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
