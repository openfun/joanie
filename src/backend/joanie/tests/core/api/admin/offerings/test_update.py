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

    def test_admin_api_offering_update_anonymous(self):
        """
        Anonymous users should not be able to update an offering.
        """
        offering = factories.OfferingFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.put(
            f"/api/v1.0/admin/offerings/{offering.id}/",
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

    def test_admin_api_offering_update_authenticated(self):
        """
        Authenticated users should not be able to update an offering.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        offering = factories.OfferingFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.put(
            f"/api/v1.0/admin/offerings/{offering.id}/",
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

    def test_admin_api_offering_update_superuser(self):
        """
        Super admin user should be able to update an offering.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.put(
            f"/api/v1.0/admin/offerings/{offering.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
                "product_id": product.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        offering.refresh_from_db()

        self.assertEqual(
            response.json(),
            {
                "id": str(offering.id),
                "uri": offering.uri,
                "can_edit": offering.can_edit,
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
                    "contract_definition": None,
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
            },
        )

    def test_admin_api_offering_partially_update_anonymous(self):
        """
        Anonymous users should not be able to partially update an offering.
        """
        offering = factories.OfferingFactory()
        course = factories.CourseFactory()
        response = self.client.patch(
            f"/api/v1.0/admin/offerings/{offering.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_admin_api_offering_partially_update_authenticated(self):
        """
        Authenticated users should not be able to partially update an offering.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        offering = factories.OfferingFactory()
        course = factories.CourseFactory()
        response = self.client.patch(
            f"/api/v1.0/admin/offerings/{offering.id}/",
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

    def test_admin_api_offering_partially_update_superuser(self):
        """
        Super admin user should be able to partially update an offering.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        course = factories.CourseFactory()
        response = self.client.patch(
            f"/api/v1.0/admin/offerings/{offering.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        offering.refresh_from_db()
        self.assertEqual(
            response.json(),
            {
                "id": str(offering.id),
                "uri": offering.uri,
                "can_edit": offering.can_edit,
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
                    "contract_definition": None,
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
            },
        )

    def test_admin_api_offering_partially_update_organizations(self):
        """
        Super admin user should be able to partially update an offering.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        offering = factories.OfferingFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        related_organizations = list(offering.organizations.all()) + [organization]
        response = self.client.patch(
            f"/api/v1.0/admin/offerings/{offering.id}/",
            content_type="application/json",
            data={
                "organization_ids": list(
                    offering.organizations.all().values_list("id", flat=True)
                )
                + [organization.id],
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        assert response.json() == {
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
                    "call_to_action": offering.course.state["call_to_action"],
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
                "contract_definition": None,
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
                for organization in related_organizations
            ],
        }

    def test_admin_api_offering_partially_update_unknown_organizations(
        self,
    ):
        """
        Updating an offering with unknown organization ids should fail.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        unknown_id_1 = uuid.uuid4()
        unknown_id_2 = uuid.uuid4()
        offering = factories.OfferingFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        response = self.client.patch(
            f"/api/v1.0/admin/offerings/{offering.id}/",
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
        offering.refresh_from_db()
        self.assertNotIn(unknown_id_1, offering.organizations.all())
        self.assertNotIn(unknown_id_2, offering.organizations.all())
        self.assertNotIn(organization, offering.organizations.all())
