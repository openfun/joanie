# pylint: disable=duplicate-code
"""
Test suite for CourseProductRelation list Admin API.
"""

from http import HTTPStatus

from django.conf import settings

from joanie.core import enums, factories
from joanie.tests.base import BaseAPITestCase


class CourseProductRelationListAdminApiTestCase(BaseAPITestCase):
    """
    Test suite for CourseProductRelation list Admin API.
    """

    maxDiff = None

    def test_admin_api_offering_list_anonymous(self):
        """
        Anonymous users should not be able to list an offering.
        """
        factories.OfferingFactory.create_batch(3)
        response = self.client.get(
            "/api/v1.0/admin/offerings/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_admin_api_offering_list_authenticated(self):
        """
        Authenticated users should not be able to list an offering.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        factories.OfferingFactory.create_batch(3)
        response = self.client.get(
            "/api/v1.0/admin/offerings/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "You do not have permission to perform this action."},
        )

    def test_admin_api_offering_list_superuser(self):
        """
        Super admin user should be able to list an offering.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offerings = factories.OfferingFactory.create_batch(
            3,
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        response = self.client.get(
            "/api/v1.0/admin/offerings/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)

        self.assertEqual(
            {
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(offering.id),
                        "uri": offering.uri,
                        "can_edit": offering.can_edit,
                        "course": {
                            "code": offering.course.code,
                            "id": str(offering.course.id),
                            "title": offering.course.title,
                            "state": {
                                "priority": offering.course.state["priority"],
                                "datetime": offering.course.state["datetime"]
                                .isoformat()
                                .replace("+00:00", "Z")
                                if offering.course.state["datetime"]
                                else None,
                                "call_to_action": offering.course.state[
                                    "call_to_action"
                                ],
                                "text": offering.course.state["text"],
                            },
                        },
                        "offering_rules": [],
                        "product": {
                            "price": float(offering.product.price),
                            "price_currency": settings.DEFAULT_CURRENCY,
                            "id": str(offering.product.id),
                            "title": offering.product.title,
                            "description": offering.product.description,
                            "call_to_action": offering.product.call_to_action,
                            "type": offering.product.type,
                            "certificate_definition": str(
                                offering.product.certificate_definition.id
                            ),
                            "contract_definition_order": None,
                            "contract_definition_batch_order": None,
                            "quote_definition": None,
                            "target_courses": [
                                str(target_course.id)
                                for target_course in offering.product.target_courses.all().order_by(
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
                            for organization in offering.organizations.all().order_by(
                                "created_on"
                            )
                        ],
                    }
                    for offering in reversed(offerings)
                ],
            },
            response.json(),
        )

    def test_admin_api_offering_list_filter_has_deep_links_true(self):
        """
        Filtering offerings with `?has_deep_links=true` should return only
        offerings that have at least one OfferingDeepLink attached.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering_with = factories.OfferingFactory(product__courses=[])
        factories.OfferingDeepLinkFactory(offering=offering_with)
        factories.OfferingFactory(product__courses=[])

        response = self.client.get(
            "/api/v1.0/admin/offerings/?has_deep_links=true",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], str(offering_with.id))

    def test_admin_api_offering_list_filter_has_deep_links_false(self):
        """
        Filtering offerings with `?has_deep_links=false` should return only
        offerings that do not have any OfferingDeepLink attached.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering_with = factories.OfferingFactory(product__courses=[])
        factories.OfferingDeepLinkFactory(offering=offering_with)
        offering_without = factories.OfferingFactory(product__courses=[])

        response = self.client.get(
            "/api/v1.0/admin/offerings/?has_deep_links=false",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], str(offering_without.id))
