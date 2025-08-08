"""Test suite for the admin batch orders API submit for signature endpoint."""

from http import HTTPStatus
from unittest import mock

from django.test import TestCase
from django.utils import timezone

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
        of a batch order if the state is not in `to_sign` or `assigned` or `quoted`.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order_states = [
            state
            for state, _ in enums.BATCH_ORDER_STATE_CHOICES
            if state
            not in [
                enums.BATCH_ORDER_STATE_ASSIGNED,
                enums.BATCH_ORDER_STATE_QUOTED,
                enums.BATCH_ORDER_STATE_TO_SIGN,
            ]
        ]

        for state in batch_order_states:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state)
                if state not in [
                    enums.BATCH_ORDER_STATE_DRAFT,
                    enums.BATCH_ORDER_STATE_CANCELED,
                ]:
                    batch_order.quote.organization_signed_on = timezone.now()
                    batch_order.quote.save()

                response = self.client.post(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/submit-for-signature/",
                    content_type="application/json",
                )

                if state in [
                    enums.BATCH_ORDER_STATE_DRAFT,
                    enums.BATCH_ORDER_STATE_CANCELED,
                ]:
                    self.assertContains(
                        response,
                        "Batch order is not eligible to get signed.",
                        status_code=HTTPStatus.BAD_REQUEST,
                    )
                else:
                    self.assertContains(
                        response,
                        "Contract is already signed by the buyer, cannot resubmit.",
                        status_code=HTTPStatus.FORBIDDEN,
                    )

    def test_api_admin_batch_orders_submit_for_signature_no_seats_left_on_active_offering_rules(
        self,
    ):
        """
        Authenticated admin user should not be able to submit for signature the contract
        of a batch order when there are no seats available on the active offering rules. This
        situation comes when the initial offering rule has not enough seats available.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED, nb_seats=10
        )

        offering_rule = factories.OfferingRuleFactory(
            nb_seats=10, course_product_relation=batch_order.offering
        )
        batch_order.offering_rules.add(offering_rule)
        batch_order.quote.organization_signed_on = timezone.now()
        batch_order.quote.save()

        # Create just 1 order into the offering rule to make it not enough for the batch order
        factories.OrderFactory(
            product=batch_order.offering.product,
            course=batch_order.offering.course,
            state=enums.ORDER_STATE_COMPLETED,
            offering_rules=[offering_rule],
        )

        response = self.client.post(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/submit-for-signature/",
            content_type="application/json",
        )

        self.assertContains(
            response,
            "Cannot submit to signature, active offering rules has no seats left",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @mock.patch("joanie.core.api.admin.send_mail_invitation_link")
    @mock.patch(
        "joanie.core.models.products.BatchOrder.submit_for_signature",
        return_value="https://dummmy.invitation_link.fr",
    )
    def test_api_admin_submit_for_signature_should_update_offering_rule_if_initial_no_seats_left(
        self, _mock_submit_for_signature, mock_send_mail_invitation_link
    ):
        """
        Authenticated admin user should be able to submit for signature the contract
        of a batch order even if the initial offering rule has not enough seats available.
        When there are other offering rules on that offering that have seats left, it should
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
                batch_order.quote.organization_signed_on = timezone.now()
                batch_order.quote.save()

                offering_rule_1 = factories.OfferingRuleFactory(
                    nb_seats=7, course_product_relation=batch_order.offering
                )
                batch_order.offering_rules.add(offering_rule_1)
                offering_rule_2 = factories.OfferingRuleFactory(
                    nb_seats=10, course_product_relation=batch_order.offering
                )

                # Create 1 order on the 1st offering rule to update the batch order to the 2nd one
                factories.OrderFactory(
                    product=batch_order.offering.product,
                    course=batch_order.offering.course,
                    state=enums.ORDER_STATE_COMPLETED,
                    offering_rules=[offering_rule_1],
                )

                response = self.client.post(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/submit-for-signature/",
                    content_type="application/json",
                )

                batch_order.refresh_from_db()

                self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)
                self.assertFalse(
                    batch_order.offering_rules.filter(pk=offering_rule_1.id).exists()
                )
                self.assertTrue(
                    batch_order.offering_rules.filter(pk=offering_rule_2.id).exists()
                )
                self.assertTrue(mock_send_mail_invitation_link.called)
                mock_send_mail_invitation_link.reset_mock()
