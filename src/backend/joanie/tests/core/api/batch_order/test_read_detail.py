"""Test suite for BatchOrder read detail API"""

from http import HTTPStatus
from unittest import mock

from django.conf import settings

from joanie.core import enums, factories
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class BatchOrderReadDetailAPITest(BaseAPITestCase):
    """Tests for BatchOrder Read detail API"""

    def test_api_batch_order_read_authenticated_fake_id(self):
        """
        Authenticated user shouldn't be able to get a response if the batch order id
        does not exist
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/batch-orders/fake_batch_order_id/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    def test_api_batch_order_read_authenticated_should_not_see_others_batch_not_owned(
        self,
    ):
        """
        Authenticated user shouldn't be able to see others batch orders that he doesn't own.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_batch_order_read_detail_authenticated(self, _mock_thumbnail):
        """
        Authenticated user should be able to see information about his batch order.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            owner=user,
            nb_seats=2,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )

        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/batch-orders/{batch_order.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertDictEqual(
            response.json(),
            {
                "id": str(batch_order.id),
                "owner": user.username,
                "payment_method": enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
                "total": float(batch_order.total),
                "currency": settings.DEFAULT_CURRENCY,
                "offering_id": str(batch_order.offering.id),
                "organization": {
                    "id": str(batch_order.organization.id),
                    "code": batch_order.organization.code,
                    "logo": "_this_field_is_mocked",
                    "title": batch_order.organization.title,
                    "address": None,
                    "enterprise_code": batch_order.organization.enterprise_code,
                    "activity_category_code": batch_order.organization.activity_category_code,
                    "contact_phone": batch_order.organization.contact_phone,
                    "contact_email": batch_order.organization.contact_email,
                    "dpo_email": batch_order.organization.dpo_email,
                },
                "main_invoice_reference": None,
                "contract_id": str(batch_order.contract.id),
                "quote": {
                    "batch_order": {
                        "company_name": batch_order.company_name,
                        "id": str(batch_order.id),
                        "organization_id": str(batch_order.organization.id),
                        "owner_name": batch_order.owner.get_full_name(),
                        "relation_id": str(batch_order.offering.id),
                        "state": enums.BATCH_ORDER_STATE_QUOTED,
                    },
                    "definition": {
                        "body": batch_order.quote.definition.body,
                        "description": batch_order.quote.definition.description,
                        "id": str(batch_order.quote.definition.id),
                        "language": batch_order.quote.definition.language,
                        "name": batch_order.quote.definition.name,
                        "title": batch_order.quote.definition.title,
                    },
                    "has_purchase_order": False,
                    "id": str(batch_order.quote.id),
                    "organization_signed_on": None,
                },
                "company_name": batch_order.company_name,
                "identification_number": batch_order.identification_number,
                "address": batch_order.address,
                "postcode": batch_order.postcode,
                "city": batch_order.city,
                "country": batch_order.country.code,
                "nb_seats": 2,
                "offering_rule_ids": [],
                "billing_address": {
                    "company_name": batch_order.company_name,
                    "identification_number": batch_order.identification_number,
                    "address": batch_order.address,
                    "postcode": batch_order.postcode,
                    "country": batch_order.billing_address["country"],
                    "contact_email": "janedoe@example.org",
                    "contact_name": "Jane Doe",
                },
                "vat_registration": None,
                "administrative_email": None,
                "administrative_firstname": None,
                "administrative_lastname": None,
                "administrative_telephone": None,
                "administrative_profession": None,
                "funding_entity": batch_order.funding_entity,
                "funding_amount": batch_order.funding_amount,
            },
        )
