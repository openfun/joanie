# pylint: disable=duplicate-code
"""
Test suite for CourseProductRelation update Admin API.
"""

import uuid
from http import HTTPStatus

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories


class CourseProductRelationUpdateAdminApiTest(TestCase):
    """
    Test suite for CourseProductRelation update Admin API.
    """

    maxDiff = None

    def test_admin_api_offer_update_anonymous(self):
        """
        Anonymous users should not be able to update an offer.
        """
        offer = factories.OfferFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.put(
            f"/api/v1.0/admin/offers/{offer.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
                "product_id": product.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_admin_api_offer_update_authenticated(self):
        """
        Authenticated users should not be able to update an offer.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        offer = factories.OfferFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.put(
            f"/api/v1.0/admin/offers/{offer.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
                "product_id": product.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "You do not have permission to perform this action."},
        )

    def test_admin_api_offer_update_superuser(self):
        """
        Super admin user should be able to update an offer.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offer = factories.OfferFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.put(
            f"/api/v1.0/admin/offers/{offer.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
                "product_id": product.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        offer.refresh_from_db()

        self.assertEqual(
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
                    for organization in offer.organizations.all().order_by("created_on")
                ],
            },
        )

    def test_admin_api_offer_partially_update_anonymous(self):
        """
        Anonymous users should not be able to partially update an offer.
        """
        offer = factories.OfferFactory()
        course = factories.CourseFactory()
        response = self.client.patch(
            f"/api/v1.0/admin/offers/{offer.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_admin_api_offer_partially_update_authenticated(self):
        """
        Authenticated users should not be able to partially update an offer.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        offer = factories.OfferFactory()
        course = factories.CourseFactory()
        response = self.client.patch(
            f"/api/v1.0/admin/offers/{offer.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "You do not have permission to perform this action."},
        )

    def test_admin_api_offer_partially_update_superuser(self):
        """
        Super admin user should be able to partially update an offer.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offer = factories.OfferFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        course = factories.CourseFactory()
        response = self.client.patch(
            f"/api/v1.0/admin/offers/{offer.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        offer.refresh_from_db()
        self.assertEqual(
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
                    for organization in offer.organizations.all().order_by("created_on")
                ],
            },
        )

    def test_admin_api_offer_partially_update_organizations(self):
        """
        Super admin user should be able to partially update an offer.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        offer = factories.OfferFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        related_organizations = list(offer.organizations.all()) + [organization]
        response = self.client.patch(
            f"/api/v1.0/admin/offers/{offer.id}/",
            content_type="application/json",
            data={
                "organization_ids": list(
                    offer.organizations.all().values_list("id", flat=True)
                )
                + [organization.id],
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        assert response.json() == {
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
                "certificate_definition": str(offer.product.certificate_definition.id),
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
                for organization in related_organizations
            ],
        }

    def test_admin_api_offer_partially_update_unknown_organizations(
        self,
    ):
        """
        Updating a offer with unknown organization ids should fail.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        unknown_id_1 = uuid.uuid4()
        unknown_id_2 = uuid.uuid4()
        offer = factories.OfferFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        response = self.client.patch(
            f"/api/v1.0/admin/offers/{offer.id}/",
            content_type="application/json",
            data={
                "organization_ids": [unknown_id_1, unknown_id_2, organization.id],
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        assert response.json() == {
            "organization_ids": [
                f"{unknown_id_1} does not exist.",
                f"{unknown_id_2} does not exist.",
            ]
        }
        offer.refresh_from_db()
        self.assertNotIn(unknown_id_1, offer.organizations.all())
        self.assertNotIn(unknown_id_2, offer.organizations.all())
        self.assertNotIn(organization, offer.organizations.all())
