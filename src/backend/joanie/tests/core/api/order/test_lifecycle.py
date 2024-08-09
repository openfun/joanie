"""Tests for the Order lifecycle through API."""

from joanie.core import enums, factories, models
from joanie.core.models import CourseState
from joanie.payment.factories import BillingAddressDictFactory, CreditCardFactory
from joanie.signature.backends import get_signature_backend
from joanie.tests.base import BaseAPITestCase


class OrderLifecycle(BaseAPITestCase):
    """
    Test the lifecycle of an order.
    """

    maxDiff = None

    def test_order_lifecycle(self):
        """
        Test the lifecycle of an order.
        """
        target_courses = factories.CourseFactory.create_batch(
            2,
            course_runs=factories.CourseRunFactory.create_batch(
                2, state=CourseState.ONGOING_OPEN
            ),
        )
        product = factories.ProductFactory(
            target_courses=target_courses,
            contract_definition=factories.ContractDefinitionFactory(),
        )
        organization = product.course_relations.first().organizations.first()

        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        data = {
            "course_code": product.courses.first().code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "billing_address": BillingAddressDictFactory(),
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.state, enums.ORDER_STATE_TO_SIGN)

        self.client.post(
            f"/api/v1.0/orders/{order.id}/submit_for_signature/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_SIGNING)

        backend = get_signature_backend()
        backend.confirm_student_signature(
            reference=order.contract.signature_backend_reference
        )

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD)

        credit_card = CreditCardFactory(owner=user)
        self.client.post(
            f"/api/v1.0/orders/{order.id}/payment-method/",
            data={"credit_card_id": str(credit_card.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

        # simulate payments
        for installment in order.payment_schedule:
            order.set_installment_paid(installment["id"])

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)
