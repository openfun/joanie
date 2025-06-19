# pylint: disable=duplicate-code
"""
Test suite for CourseProductRelation create Admin API.
"""

import uuid
from http import HTTPStatus

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories, models


class CourseProductRelationCreateAdminApiTest(TestCase):
    """
    Test suite for CourseProductRelation create Admin API.
    """

    maxDiff = None

    def test_admin_api_offer_create_anonymous(self):
        """
        Anonymous users should not be able to create an offer.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        organization = factories.OrganizationFactory()
        response = self.client.post(
            "/api/v1.0/admin/offers/",
            {
                "course_id": course.id,
                "product_id": product.id,
                "organization_ids": [organization.id],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_admin_api_offer_create_authenticated(self):
        """
        Authenticated users should not be able to create an offer.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        organization = factories.OrganizationFactory()
        response = self.client.post(
            "/api/v1.0/admin/offers/",
            {
                "course_id": course.id,
                "product_id": product.id,
                "organization_ids": [organization.id],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "You do not have permission to perform this action."},
        )

    def test_admin_api_offer_create_superuser(self):
        """
        Super admin user should be able to create an offer.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        organization = factories.OrganizationFactory()
        response = self.client.post(
            "/api/v1.0/admin/offers/",
            {
                "course_id": course.id,
                "product_id": product.id,
                "organization_ids": [organization.id],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        offer = models.CourseProductRelation.objects.get(id=response.json()["id"])

        self.assertDictEqual(
            response.json(),
            {
                "id": str(offer.id),
                "uri": offer.uri,
                "can_edit": offer.can_edit,
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "state": {
                        "priority": course.state["priority"],
                        "datetime": course.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if course.state["datetime"]
                        else None,
                        "call_to_action": course.state["call_to_action"],
                        "text": course.state["text"],
                    },
                },
                "offer_rules": [],
                "product": {
                    "price": float(product.price),
                    "price_currency": settings.DEFAULT_CURRENCY,
                    "id": str(product.id),
                    "title": product.title,
                    "description": product.description,
                    "call_to_action": product.call_to_action,
                    "type": product.type,
                    "certificate_definition": str(product.certificate_definition.id),
                    "contract_definition": None,
                    "target_courses": [
                        str(target_course.id)
                        for target_course in product.target_courses.all().order_by(
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
                ],
            },
        )

    def test_admin_api_offer_create_no_course_id(self):
        """
        Create an offer without course id should fail.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        organization = factories.OrganizationFactory()

        response = self.client.post(
            "/api/v1.0/admin/offers/",
            {
                "product_id": product.id,
                "organization_ids": [organization.id],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"course_id": "This field is required."},
        )

    def test_admin_api_offer_create_no_product_id(self):
        """
        Create an offer without product id should fail.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        organization = factories.OrganizationFactory()

        response = self.client.post(
            "/api/v1.0/admin/offers/",
            {
                "course_id": course.id,
                "organization_ids": [organization.id],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"product_id": "This field is required."},
        )

    def test_admin_api_offer_create_no_organization_id(self):
        """
        Super admin user should be able to create an offer
        without organization id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.post(
            "/api/v1.0/admin/offers/",
            {
                "course_id": course.id,
                "product_id": product.id,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        offer = models.CourseProductRelation.objects.get(id=response.json()["id"])

        self.assertDictEqual(
            response.json(),
            {
                "id": str(offer.id),
                "uri": offer.uri,
                "can_edit": offer.can_edit,
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "state": {
                        "priority": course.state["priority"],
                        "datetime": course.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if course.state["datetime"]
                        else None,
                        "call_to_action": course.state["call_to_action"],
                        "text": course.state["text"],
                    },
                },
                "offer_rules": [],
                "product": {
                    "price": float(product.price),
                    "price_currency": settings.DEFAULT_CURRENCY,
                    "id": str(product.id),
                    "title": product.title,
                    "description": product.description,
                    "call_to_action": product.call_to_action,
                    "type": product.type,
                    "certificate_definition": str(product.certificate_definition.id),
                    "contract_definition": None,
                    "target_courses": [
                        str(target_course.id)
                        for target_course in product.target_courses.all().order_by(
                            "product_target_relations__position"
                        )
                    ],
                },
                "organizations": [],
            },
        )

    def test_admin_api_offer_create_no_payload(self):
        """
        Super admin user should be able to create an offer
        without payload.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.post(
            "/api/v1.0/admin/offers/",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "course_id": "This field is required.",
                "product_id": "This field is required.",
            },
        )

    def test_admin_api_offer_create_unknown_organization(self):
        """
        Creating a offer with unknown organization ids should fail.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        unknown_id_1 = uuid.uuid4()
        unknown_id_2 = uuid.uuid4()
        organization = factories.OrganizationFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.post(
            "/api/v1.0/admin/offers/",
            {
                "course_id": course.id,
                "product_id": product.id,
                "organization_ids": [unknown_id_1, unknown_id_2, organization.id],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        assert response.json() == {
            "organization_ids": [
                f"{unknown_id_1} does not exist.",
                f"{unknown_id_2} does not exist.",
            ]
        }
        organization.refresh_from_db()
        self.assertEqual(organization.offers.count(), 0)
