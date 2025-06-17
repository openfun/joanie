# pylint: disable=duplicate-code
"""
Test suite for CourseProductRelation list Admin API.
"""

from http import HTTPStatus

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories


class CourseProductRelationListAdminApiTest(TestCase):
    """
    Test suite for CourseProductRelation list Admin API.
    """

    maxDiff = None

    def test_admin_api_offer_list_anonymous(self):
        """
        Anonymous users should not be able to list an offer.
        """
        factories.OfferFactory.create_batch(3)
        response = self.client.get(
            "/api/v1.0/admin/offers/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_admin_api_offer_list_authenticated(self):
        """
        Authenticated users should not be able to list an offer.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        factories.OfferFactory.create_batch(3)
        response = self.client.get(
            "/api/v1.0/admin/offers/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "You do not have permission to perform this action."},
        )

    def test_admin_api_offer_list_superuser(self):
        """
        Super admin user should be able to list an offer.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offers = factories.OfferFactory.create_batch(
            3,
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        response = self.client.get(
            "/api/v1.0/admin/offers/",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertEqual(
            response.json(),
            {
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(offer.id),
                        "uri": offer.uri,
                        "can_edit": offer.can_edit,
                        "course": {
                            "code": offer.course.code,
                            "id": str(offer.course.id),
                            "title": offer.course.title,
                            "state": {
                                "priority": offer.course.state["priority"],
                                "datetime": offer.course.state["datetime"]
                                .isoformat()
                                .replace("+00:00", "Z")
                                if offer.course.state["datetime"]
                                else None,
                                "call_to_action": offer.course.state["call_to_action"],
                                "text": offer.course.state["text"],
                            },
                        },
                        "offer_rules": [],
                        "product": {
                            "price": float(offer.product.price),
                            "price_currency": settings.DEFAULT_CURRENCY,
                            "id": str(offer.product.id),
                            "title": offer.product.title,
                            "description": offer.product.description,
                            "call_to_action": offer.product.call_to_action,
                            "type": offer.product.type,
                            "certificate_definition": str(
                                offer.product.certificate_definition.id
                            ),
                            "contract_definition": None,
                            "target_courses": [
                                str(target_course.id)
                                for target_course in offer.product.target_courses.all().order_by(
                                    "product_target_relations__position"
                                )
                            ],
                        },
                        "organizations": [
                            {
                                "code": organization.code,
                                "id": str(organization.id),
                                "title": organization.title,
                            }
                            for organization in offer.organizations.all().order_by(
                                "created_on"
                            )
                        ],
                    }
                    for offer in reversed(offers)
                ],
            },
        )
