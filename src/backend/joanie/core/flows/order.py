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
    def assign(self, billing_address=None):
        """
        Transition order to assigned state.
        """
        if not self.instance.is_free and billing_address:
            Address = apps.get_model("core", "Address")  # pylint: disable=invalid-name
            address, _ = Address.objects.get_or_create(
                **billing_address,
                owner=self.instance.owner,
                defaults={
                    "is_reusable": False,
                    "title": f"Billing address of order {self.instance.id}",
                },
            )

            # Create the main invoice
            Invoice = apps.get_model("payment", "Invoice")  # pylint: disable=invalid-name
            Invoice.objects.get_or_create(
                order=self.instance,
                total=self.instance.total,
                recipient_address=address,
            )

        self.instance.freeze_target_courses()
        self.update()

    def _can_be_state_completed_from_assigned(self):
        """
        An order state can be set to completed if the order is free
        and has no unsigned contract
        """
        return self.instance.is_free and not self.instance.has_unsigned_contract

    def _can_be_state_to_sign_and_to_save_payment_method(self):
        """
        An order state can be set to to_sign_and_to_save_payment_method if the order is not free
        and has no payment method and an unsigned contract
        """
        return (
            not self.instance.is_free
            and not self.instance.has_payment_method
            and self.instance.has_unsigned_contract
        )

    def _can_be_state_to_save_payment_method(self):
        """
        An order state can be set to_save_payment_method if the order is not free
        and has no payment method and no unsigned contract.
        """
        return (
            not self.instance.is_free
            and not self.instance.has_payment_method
            and not self.instance.has_unsigned_contract
        )

    def _can_be_state_to_sign(self):
        """
        An order state can be set to to_sign if the order is free
        or has a payment method and an unsigned contract.
        """
        return (
            self.instance.is_free or self.instance.has_payment_method
        ) and self.instance.has_unsigned_contract

    def _can_be_state_pending_from_assigned(self):
        """
        An order state can be set to pending if the order is not free
        and has a payment method and no contract to sign.
        """
        return (
            self.instance.is_free or self.instance.has_payment_method
        ) and not self.instance.has_unsigned_contract

    @state.transition(
        source=enums.ORDER_STATE_ASSIGNED,
        target=enums.ORDER_STATE_COMPLETED,
        conditions=[_can_be_state_completed_from_assigned],
    )
    def complete_from_assigned(self):
        """
        Transition order to completed state.
        """

    @state.transition(
        source=enums.ORDER_STATE_ASSIGNED,
        target=enums.ORDER_STATE_TO_SIGN_AND_TO_SAVE_PAYMENT_METHOD,
        conditions=[_can_be_state_to_sign_and_to_save_payment_method],
    )
    def to_sign_and_to_save_payment_method(self):
        """
        Transition order to to_sign_and_to_save_payment_method state.
        """

    @state.transition(
        source=[
            enums.ORDER_STATE_ASSIGNED,
            enums.ORDER_STATE_TO_SIGN_AND_TO_SAVE_PAYMENT_METHOD,
        ],
        target=enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
        conditions=[_can_be_state_to_save_payment_method],
    )
    def to_save_payment_method(self):
        """
        Transition order to to_save_payment_method state.
        """

    @state.transition(
        source=[
            enums.ORDER_STATE_ASSIGNED,
            enums.ORDER_STATE_TO_SIGN_AND_TO_SAVE_PAYMENT_METHOD,
        ],
        target=enums.ORDER_STATE_TO_SIGN,
        conditions=[_can_be_state_to_sign],
    )
    def to_sign(self):
        """
        Transition order to to_sign state.
        """

    @state.transition(
        source=enums.ORDER_STATE_ASSIGNED,
        target=enums.ORDER_STATE_PENDING,
        conditions=[_can_be_state_pending_from_assigned],
    )
    def pending_from_assigned(self):
        """
        Transition order to pending state.
        """

    def update(self):
        """
        Update the order state.
        """
        if self._can_be_state_completed_from_assigned():
            self.complete_from_assigned()
            return

        if self._can_be_state_to_sign_and_to_save_payment_method():
            self.to_sign_and_to_save_payment_method()
            return

        if self._can_be_state_to_save_payment_method():
            self.to_save_payment_method()
            return

        if self._can_be_state_to_sign():
            self.to_sign()
            return

        if self._can_be_state_pending_from_assigned():
            self.pending_from_assigned()
            return

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
        source=[
            enums.ORDER_STATE_DRAFT,
            enums.ORDER_STATE_ASSIGNED,
            enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            enums.ORDER_STATE_PENDING,
        ],
        target=enums.ORDER_STATE_SUBMITTED,
        conditions=[_can_be_state_submitted],
    )
    def submit(self, billing_address=None, credit_card_id=None):
        """
        Transition order to submitted state.
        Create a payment if the product is fee
        """
        # CreditCard = apps.get_model("payment", "CreditCard")  # pylint: disable=invalid-name
        # payment_backend = get_payment_backend()
        # if credit_card_id:
        #     try:
        #         credit_card = CreditCard.objects.get(
        #             owner=self.instance.owner, id=credit_card_id
        #         )
        #         return payment_backend.create_one_click_payment(
        #             order=self.instance,
        #             billing_address=billing_address,
        #             credit_card_token=credit_card.token,
        #         )
        #     except (CreditCard.DoesNotExist, NotImplementedError):
        #         pass
        # payment_info = payment_backend.create_payment(
        #     order=self.instance, billing_address=billing_address
        # )
        #
        # return payment_info

    @state.transition(
        source=[
            enums.ORDER_STATE_DRAFT,
            enums.ORDER_STATE_ASSIGNED,
            enums.ORDER_STATE_SUBMITTED,
            enums.ORDER_STATE_PENDING,
            enums.ORDER_STATE_COMPLETED,
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
    def _post_transition_success(self, descriptor, source, target, **kwargs):  # pylint: disable=unused-argument
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
