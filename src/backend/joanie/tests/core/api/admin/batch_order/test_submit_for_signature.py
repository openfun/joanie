"""Test suite for the admin batch orders API submit for signature endpoint."""

from http import HTTPStatus
from unittest import mock

from django.test import TestCase

from joanie.core import enums, factories


class BatchOrdersAdminApiSubmitForSignatureTestCase(TestCase):
    """Test suite for the admin batch orders API submit for signature endpoint."""

    def test_api_admin_batch_orders_submit_for_signature_anonymous(self):
        """
        Anonymous user shouldn't be able to submit for signature the contract of a batch order.
        """

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/submit-for-signature/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_batch_orders_submit_for_signature_not_admin_user(self):
        """
        Authenticated not admin user shouldn't be able to submit for signature the contract of a
        batch order.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/submit-for-signature/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_batch_orders_submit_for_signature_state_not_assigned_or_to_sign(
        self,
    ):
        """
        Authenticated admin user should not be able to submit for signature the contract
        of a batch order if the state is not in `to_sign` or `assigned`.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order_states = [
            state
            for state, _ in enums.BATCH_ORDER_STATE_CHOICES
            if state
            not in [enums.BATCH_ORDER_STATE_ASSIGNED, enums.BATCH_ORDER_STATE_TO_SIGN]
        ]

        for state in batch_order_states:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state)

                response = self.client.post(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/submit-for-signature/",
                    content_type="application/json",
                )

                self.assertContains(
                    response,
                    "Batch order state should be `assigned` or `to_sign`.",
                    status_code=HTTPStatus.BAD_REQUEST,
                )

    def test_api_admin_batch_orders_submit_for_signature_when_no_seats_left_on_active_offer_rules(
        self,
    ):
        """
        Authenticated admin user should not be able to submit for signature the contract
        of a batch order when there are no seats available on the active offer rules. This
        situation comes when the initial offer rule has not enough seats available.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED, nb_seats=10
        )

        offer_rule = factories.OfferRuleFactory(
            nb_seats=10, course_product_relation=batch_order.relation
        )
        batch_order.offer_rules.add(offer_rule)

        # Create just 1 order into the offer rule to make it not enough for the batch order
        factories.OrderFactory(
            product=batch_order.relation.product,
            course=batch_order.relation.course,
            state=enums.ORDER_STATE_COMPLETED,
            offer_rules=[offer_rule],
        )

        response = self.client.post(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/submit-for-signature/",
            content_type="application/json",
        )

        self.assertContains(
            response,
            "Cannot submit to signature, active offer rules has no seats left",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @mock.patch("joanie.core.api.admin.send_mail_invitation_link")
    @mock.patch(
        "joanie.core.models.products.BatchOrder.submit_for_signature",
        return_value="https://dummmy.invitation_link.fr",
    )
    def test_api_admin_submit_for_signature_should_update_offer_rule_if_initial_no_seats_left(
        self, _mock_submit_for_signature, mock_send_mail_invitation_link
    ):
        """
        Authenticated admin user should be able to submit for signature the contract
        of a batch order even if the initial offer rule has not enough seats available.
        When there are other offer rules on that relation that have seats left, it should
        replace it to a new one with the seats available. And finally, it should send the
        invitation link to the owner.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        for state in [
            enums.BATCH_ORDER_STATE_ASSIGNED,
            enums.BATCH_ORDER_STATE_TO_SIGN,
        ]:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state, nb_seats=7)

                offer_rule_1 = factories.OfferRuleFactory(
                    nb_seats=7, course_product_relation=batch_order.relation
                )
                batch_order.offer_rules.add(offer_rule_1)
                offer_rule_2 = factories.OfferRuleFactory(
                    nb_seats=10, course_product_relation=batch_order.relation
                )

                # Create 1 order on the 1st offer rule to update the batch order to the 2nd one
                factories.OrderFactory(
                    product=batch_order.relation.product,
                    course=batch_order.relation.course,
                    state=enums.ORDER_STATE_COMPLETED,
                    offer_rules=[offer_rule_1],
                )

                response = self.client.post(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/submit-for-signature/",
                    content_type="application/json",
                )

                batch_order.refresh_from_db()

                self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)
                self.assertFalse(
                    batch_order.offer_rules.filter(pk=offer_rule_1.id).exists()
                )
                self.assertTrue(
                    batch_order.offer_rules.filter(pk=offer_rule_2.id).exists()
                )
                self.assertTrue(mock_send_mail_invitation_link.called)
                mock_send_mail_invitation_link.reset_mock()
