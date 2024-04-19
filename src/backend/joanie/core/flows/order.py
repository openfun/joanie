"""Order flows."""

from django.apps import apps
from django.utils import timezone

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
                credit_card = CreditCard.objects.get(
                    owner=self.instance.owner, id=credit_card_id
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

    @state.on_success()
    def _post_transition_success(self, descriptor, source, target):  # pylint: disable=unused-argument
        """Post transition actions"""
        self.instance.save()

        # When an order is validated, if the user was previously enrolled for free in any of the
        # course runs targeted by the purchased product, we should change their enrollment mode on
        # these course runs to "verified".
        if target in [enums.ORDER_STATE_VALIDATED, enums.ORDER_STATE_CANCELED]:
            Enrollment = apps.get_model("core", "Enrollment")  # pylint: disable=invalid-name
            for enrollment in Enrollment.objects.filter(
                course_run__course__target_orders=self.instance, is_active=True
            ).select_related("course_run", "user"):
                enrollment.set()

        # Only enroll user if the product has no contract to sign, otherwise we should wait
        # for the contract to be signed before enrolling the user.
        if (
            target == enums.ORDER_STATE_VALIDATED
            and self.instance.product.contract_definition is None
        ):
            self.instance.enroll_user_to_course_run()

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
