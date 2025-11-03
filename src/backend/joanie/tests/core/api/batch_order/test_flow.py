"""Test suite of full flow of batch order cycle through API endpoints"""

import json
from http import HTTPStatus
from unittest import mock

from django.urls import reverse

from rest_framework.test import APIRequestFactory

from joanie.core import enums, factories, models
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.tests.base import BaseAPITestCase


class BatchOrderFullFlowAPITest(BaseAPITestCase):
    """
    Test suite of full flow of batch order cycle through API endpoints
    for every payment methods available.
    """

    def build_batch_order_payload(self, payment_method: str) -> dict:
        """
        Returns simple batch order sample for create payload.
        """
        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )

        return {
            "offering_id": offering.id,
            "nb_seats": 2,
            "company_name": "Acme Org",
            "identification_number": "123",
            "address": "Street of awesomeness",
            "city": "Paradise",
            "postcode": "2900",
            "country": "FR",
            "payment_method": payment_method,
            "organization_id": offering.organizations.first().id,
            "billing_address": {
                "company_name": " Acme Corp",
                "identification_number": "456",
                "address": "Street of Hogwarts",
                "postcode": "75000",
                "country": "FR",
                "contact_email": "jane@example.org",
                "contact_name": "Jane Doe",
                "city": "Paris",
            },
            "administrative_firstname": "John",
            "administrative_lastname": "Wick",
            "administrative_profession": "Human Resources",
            "administrative_email": "example@example.org",
            "administrative_telephone": "0123456789",
            "signatory_firstname": "Jane",
            "signatory_lastname": "Doe",
            "signatory_profession": "General Directory",
            "signatory_email": "example2@example.org",
            "signatory_telephone": "0987654321",
        }

    @mock.patch.object(
        DummyPaymentBackend,
        "create_payment",
        side_effect=DummyPaymentBackend().create_payment,
    )
    def test_batch_order_flow_payment_method_card_payment(self, mock_create_payment):
        """Test the full flow of batch order with card payment through the API endpoints"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=self.build_batch_order_payload(enums.BATCH_ORDER_WITH_CARD_PAYMENT),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

        batch_order = models.BatchOrder.objects.get()
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_QUOTED)

        # From the point of view of the organization
        organization = batch_order.organization
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role=enums.OWNER
        )
        organization_owner_token = self.generate_token_from_user(access.user)

        # Confirm the quote
        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/confirm-quote/",
            HTTP_AUTHORIZATION=f"Bearer {organization_owner_token}",
            content_type="application/json",
            data={
                "quote_id": str(batch_order.quote.id),
                "total": "100.00",
            },
        )
        batch_order.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)

        # Submit for signature contract
        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature-batch-order/",
            data={"batch_order_id": str(batch_order.id)},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {organization_owner_token}",
        )

        batch_order.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.ACCEPTED)
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PENDING)

        response = self.client.post(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-payment/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        mock_create_payment.assert_called_once_with(
            order=batch_order,
            billing_address=batch_order.create_billing_address(),
            installment=None,
        )

        batch_order.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PROCESS_PAYMENT)
        self.assertEqual(
            response.json(),
            {
                "payment_id": str(batch_order.offering.product.id),
                "provider_name": "dummy",
                "url": "https://example.com/api/v1.0/payments/notifications",
            },
        )

        # Notify that the payment has succeeded
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={
                "id": str(batch_order.offering.product.id),
                "type": "payment",
                "state": "success",
            },
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))
        backend = DummyPaymentBackend()

        backend.handle_notification(request)

        batch_order.refresh_from_db()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)
        # The orders should be generated with the voucher codes
        self.assertTrue(batch_order.orders.exists())

    def test_batch_order_flow_payment_method_bank_transfer(self):
        """Test the full flow of batch order with bank transfer through the API endpoints"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=self.build_batch_order_payload(enums.BATCH_ORDER_WITH_BANK_TRANSFER),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

        batch_order = models.BatchOrder.objects.get()
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_QUOTED)

        organization = batch_order.organization
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role=enums.OWNER
        )
        organization_owner_token = self.generate_token_from_user(access.user)

        # Confirm the quote
        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/confirm-quote/",
            HTTP_AUTHORIZATION=f"Bearer {organization_owner_token}",
            content_type="application/json",
            data={
                "quote_id": str(batch_order.quote.id),
                "total": "1245.00",
            },
        )
        batch_order.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)

        # Submit for signature contract
        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature-batch-order/",
            data={"batch_order_id": str(batch_order.id)},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {organization_owner_token}",
        )

        batch_order.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.ACCEPTED)
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PENDING)

        # Confirm bank transfer
        response = self.client.post(
            f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-bank-transfer/",
            data={"batch_order_id": str(batch_order.id)},
            HTTP_AUTHORIZATION=f"Bearer {organization_owner_token}",
        )

        batch_order.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)
        # The orders should be generated with the voucher codes
        self.assertTrue(batch_order.orders.exists())

    def test_batch_order_flow_payment_method_purchase_order(self):
        """Test the full flow of batch order with purchase order through the API endpoints"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.post(
            "/api/v1.0/batch-orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=self.build_batch_order_payload(enums.BATCH_ORDER_WITH_PURCHASE_ORDER),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)

        batch_order = models.BatchOrder.objects.get()
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_QUOTED)

        # From the point of view of the organization
        organization = batch_order.organization
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role=enums.OWNER
        )
        organization_owner_token = self.generate_token_from_user(access.user)

        # Confirm the quote
        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/confirm-quote/",
            HTTP_AUTHORIZATION=f"Bearer {organization_owner_token}",
            content_type="application/json",
            data={
                "quote_id": str(batch_order.quote.id),
                "total": "100.00",
            },
        )
        batch_order.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)

        # Confirm purchase order
        response = self.client.patch(
            f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-purchase-order/",
            data={"quote_id": str(batch_order.quote.id)},
            HTTP_AUTHORIZATION=f"Bearer {organization_owner_token}",
            content_type="application/json",
        )

        batch_order.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(batch_order.quote.has_purchase_order, True)
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)

        # Submit for signature contract
        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature-batch-order/",
            data={"batch_order_id": str(batch_order.id)},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {organization_owner_token}",
        )

        batch_order.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.ACCEPTED)
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)
        self.assertTrue(batch_order.orders.exists())
