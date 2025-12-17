"""Test suite for BatchOrder list API"""

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

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

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
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )

        with self.record_performance():
            response = self.client.get(
                "/api/v1.0/batch-orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)

        self.assertDictEqual(
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(bo.id),
                        "owner": user.username,
                        "payment_method": enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
                        "state": enums.BATCH_ORDER_STATE_QUOTED,
                        "total": float(bo.total),
                        "currency": settings.DEFAULT_CURRENCY,
                        "offering": {
                            "id": str(bo.offering.id),
                            "course": {
                                "id": str(bo.offering.course.id),
                                "title": bo.offering.course.title,
                                "code": bo.offering.course.code,
                                "cover": "_this_field_is_mocked",
                            },
                            "product": {
                                "id": str(bo.offering.product.id),
                                "title": bo.offering.product.title,
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
                        "main_invoice_reference": None,
                        "contract_id": str(bo.contract.id),
                        "quote": {
                            "id": str(bo.quote.id),
                            "has_purchase_order": False,
                            "organization_signed_on": None,
                        },
                        "company_name": bo.company_name,
                        "identification_number": bo.identification_number,
                        "address": bo.address,
                        "postcode": bo.postcode,
                        "city": bo.city,
                        "country": bo.country.code,
                        "nb_seats": 2,
                        "offering_rule_ids": [],
                        "billing_address": {
                            "company_name": bo.company_name,
                            "identification_number": bo.identification_number,
                            "address": bo.address,
                            "postcode": bo.postcode,
                            "country": bo.billing_address["country"],
                            "city": bo.billing_address["city"],
                            "contact_name": "Jane Doe",
                            "contact_email": "janedoe@example.org",
                        },
                        "vat_registration": None,
                        "administrative_email": None,
                        "administrative_firstname": None,
                        "administrative_lastname": None,
                        "administrative_telephone": None,
                        "administrative_profession": None,
                        "signatory_email": bo.signatory_email,
                        "signatory_firstname": bo.signatory_firstname,
                        "signatory_lastname": bo.signatory_lastname,
                        "signatory_telephone": bo.signatory_telephone,
                        "signatory_profession": bo.signatory_profession,
                        "funding_entity": bo.funding_entity,
                        "funding_amount": float(bo.funding_amount),
                        "available_actions": {
                            "confirm_quote": True,
                            "confirm_purchase_order": False,
                            "confirm_bank_transfer": False,
                            "submit_for_signature": False,
                            "next_action": "confirm_quote",
                        },
                    },
                ],
            },
            response.json(),
        )
