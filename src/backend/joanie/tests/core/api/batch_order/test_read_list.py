"""Test suite for BatchOrder read list API"""

from http import HTTPStatus
from unittest import mock

from django.conf import settings

from joanie.core import enums, factories
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class BatchOrderReadListAPITest(BaseAPITestCase):
    """Tests for BatchOrder Read list API"""

    def test_api_batch_read_order_anonymous(self):
        """
        Anonymous user shouldn't be able to see batch orders list
        """
        factories.BatchOrderFactory.create_batch(3)

        response = self.client.get(
            "/api/v1.0/batch-orders/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_batch_order_read_authenticated_get_list(self, _mock_thumbnail):
        """
        Authenticated user should be able to see his batch order only.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.BatchOrderFactory()  # Create batch order not owned by the user
        bo = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            owner=user,
            nb_seats=2,
            trainees=[
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Doe"},
            ],
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )

        with self.record_performance():
            response = self.client.get(
                "/api/v1.0/batch-orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())

        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(bo.id),
                        "owner": user.username,
                        "payment_method": enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
                        "total": bo.total,
                        "currency": settings.DEFAULT_CURRENCY,
                        "offering_id": str(bo.offering.id),
                        "organization": {
                            "id": str(bo.organization.id),
                            "code": bo.organization.code,
                            "logo": "_this_field_is_mocked",
                            "title": bo.organization.title,
                            "address": None,
                            "enterprise_code": bo.organization.enterprise_code,
                            "activity_category_code": bo.organization.activity_category_code,
                            "contact_phone": bo.organization.contact_phone,
                            "contact_email": bo.organization.contact_email,
                            "dpo_email": bo.organization.dpo_email,
                        },
                        "main_invoice_reference": None,
                        "contract_id": str(bo.contract.id),
                        "quote": {
                            "batch_order": {
                                "company_name": bo.company_name,
                                "id": str(bo.id),
                                "organization_id": str(bo.organization.id),
                                "owner_name": bo.owner.get_full_name(),
                                "relation_id": str(bo.offering.id),
                                "state": enums.BATCH_ORDER_STATE_QUOTED,
                            },
                            "definition": {
                                "body": bo.quote.definition.body,
                                "description": bo.quote.definition.description,
                                "id": str(bo.quote.definition.id),
                                "language": bo.quote.definition.language,
                                "name": bo.quote.definition.name,
                                "title": bo.quote.definition.title,
                            },
                            "has_purchase_order": False,
                            "id": str(bo.quote.id),
                            "organization_signed_on": None,
                        },
                        "company_name": bo.company_name,
                        "identification_number": bo.identification_number,
                        "address": bo.address,
                        "postcode": bo.postcode,
                        "city": bo.city,
                        "country": bo.country.code,
                        "nb_seats": 2,
                        "trainees": [
                            {"last_name": "Doe", "first_name": "John"},
                            {"last_name": "Doe", "first_name": "Jane"},
                        ],
                        "offering_rule_ids": [],
                    },
                ],
            },
        )
