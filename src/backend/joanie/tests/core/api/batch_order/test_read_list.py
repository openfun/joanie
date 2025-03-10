"""Test suite for BatchOrder read list API"""

from http import HTTPStatus
from unittest import mock

from django.conf import settings

from joanie.core import factories
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
            relation__product__contract_definition=factories.ContractDefinitionFactory(),
            relation__product__certificate_definition=None,
            owner=user,
            nb_seats=2,
            trainees=[
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Doe"},
            ],
        )
        bo.init_flow()

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
                        "total": float(bo.total),
                        "currency": settings.DEFAULT_CURRENCY,
                        "relation": {
                            "course": {
                                "id": str(bo.relation.course.id),
                                "code": bo.relation.course.code,
                                "cover": "_this_field_is_mocked",
                                "title": bo.relation.course.title,
                            },
                            "created_on": bo.relation.created_on.strftime(
                                "%Y-%m-%dT%H:%M:%S.%fZ"
                            ),
                            "id": str(bo.relation.id),
                            "order_groups": [],
                            "product": {
                                "call_to_action": "let's go!",
                                "certificate_definition": None,
                                "contract_definition": {
                                    "id": str(
                                        bo.relation.product.contract_definition.id
                                    ),
                                    "description": (
                                        bo.relation.product.contract_definition.description
                                    ),
                                    "language": bo.relation.product.contract_definition.language,
                                    "title": bo.relation.product.contract_definition.title,
                                },
                                "id": str(bo.relation.product.id),
                                "instructions": "",
                                "price": float(bo.relation.product.price),
                                "price_currency": settings.DEFAULT_CURRENCY,
                                "state": {
                                    "priority": bo.relation.product.state["priority"],
                                    "datetime": None,
                                    "call_to_action": None,
                                    "text": "to be scheduled",
                                },
                                "target_courses": [],
                                "title": bo.relation.product.title,
                                "type": bo.relation.product.type,
                            },
                        },
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
                        "main_invoice_reference": bo.main_invoice.reference,
                        "contract_id": str(bo.contract.id),
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
                    },
                ],
            },
        )
