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

    def test_admin_api_course_products_relation_update_anonymous(self):
        """
        Anonymous users should not be able to update a course product relation.
        """
        relation = factories.CourseProductRelationFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.put(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
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

    def test_admin_api_course_products_relation_update_authenticated(self):
        """
        Authenticated users should not be able to update a course product relation.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        relation = factories.CourseProductRelationFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.put(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
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

    def test_admin_api_course_products_relation_update_superuser(self):
        """
        Super admin user should be able to update a course product relation.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.put(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
                "product_id": product.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        relation.refresh_from_db()

        self.assertEqual(
            response.json(),
            {
                "id": str(relation.id),
                "uri": relation.uri,
                "can_edit": relation.can_edit,
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
                    "price": float(relation.product.price),
                    "price_currency": settings.DEFAULT_CURRENCY,
                    "id": str(relation.product.id),
                    "title": relation.product.title,
                    "description": relation.product.description,
                    "call_to_action": relation.product.call_to_action,
                    "type": relation.product.type,
                    "certificate_definition": str(
                        relation.product.certificate_definition.id
                    ),
                    "contract_definition": None,
                    "target_courses": [
                        str(target_course.id)
                        for target_course in relation.product.target_courses.all().order_by(
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
                    for organization in relation.organizations.all().order_by(
                        "created_on"
                    )
                ],
            },
        )

    def test_admin_api_course_products_relation_partially_update_anonymous(self):
        """
        Anonymous users should not be able to partially update a course product relation.
        """
        relation = factories.CourseProductRelationFactory()
        course = factories.CourseFactory()
        response = self.client.patch(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_admin_api_course_products_relation_partially_update_authenticated(self):
        """
        Authenticated users should not be able to partially update a course product relation.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        relation = factories.CourseProductRelationFactory()
        course = factories.CourseFactory()
        response = self.client.patch(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
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

    def test_admin_api_course_products_relation_partially_update_superuser(self):
        """
        Super admin user should be able to partially update a course product relation.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        course = factories.CourseFactory()
        response = self.client.patch(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
            content_type="application/json",
            data={
                "course_id": course.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        relation.refresh_from_db()
        self.assertEqual(
            response.json(),
            {
                "id": str(relation.id),
                "uri": relation.uri,
                "can_edit": relation.can_edit,
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
                    "price": float(relation.product.price),
                    "price_currency": settings.DEFAULT_CURRENCY,
                    "id": str(relation.product.id),
                    "title": relation.product.title,
                    "description": relation.product.description,
                    "call_to_action": relation.product.call_to_action,
                    "type": relation.product.type,
                    "certificate_definition": str(
                        relation.product.certificate_definition.id
                    ),
                    "contract_definition": None,
                    "target_courses": [
                        str(target_course.id)
                        for target_course in relation.product.target_courses.all().order_by(
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
                    for organization in relation.organizations.all().order_by(
                        "created_on"
                    )
                ],
            },
        )

    def test_admin_api_course_products_relation_partially_update_organizations(self):
        """
        Super admin user should be able to partially update a course product relation.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        related_organizations = list(relation.organizations.all()) + [organization]
        response = self.client.patch(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
            content_type="application/json",
            data={
                "organization_ids": list(
                    relation.organizations.all().values_list("id", flat=True)
                )
                + [organization.id],
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        assert response.json() == {
            "id": str(relation.id),
            "uri": relation.uri,
            "can_edit": relation.can_edit,
            "course": {
                "code": relation.course.code,
                "id": str(relation.course.id),
                "title": relation.course.title,
                "state": {
                    "priority": relation.course.state["priority"],
                    "datetime": relation.course.state["datetime"]
                    .isoformat()
                    .replace("+00:00", "Z")
                    if relation.course.state["datetime"]
                    else None,
                    "call_to_action": relation.course.state["call_to_action"],
                    "text": relation.course.state["text"],
                },
            },
            "offer_rules": [],
            "product": {
                "price": float(relation.product.price),
                "price_currency": settings.DEFAULT_CURRENCY,
                "id": str(relation.product.id),
                "title": relation.product.title,
                "description": relation.product.description,
                "call_to_action": relation.product.call_to_action,
                "type": relation.product.type,
                "certificate_definition": str(
                    relation.product.certificate_definition.id
                ),
                "contract_definition": None,
                "target_courses": [
                    str(target_course.id)
                    for target_course in relation.product.target_courses.all().order_by(
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

    def test_admin_api_course_products_relation_partially_update_unknown_organizations(
        self,
    ):
        """
        Updating a relation with unknown organization ids should fail.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        unknown_id_1 = uuid.uuid4()
        unknown_id_2 = uuid.uuid4()
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        response = self.client.patch(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
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
        relation.refresh_from_db()
        self.assertNotIn(unknown_id_1, relation.organizations.all())
        self.assertNotIn(unknown_id_2, relation.organizations.all())
        self.assertNotIn(organization, relation.organizations.all())
