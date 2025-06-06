# pylint: disable=duplicate-code
"""
Test suite for CourseProductRelation retrieve Admin API.
"""

from http import HTTPStatus

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories


class CourseProductRelationRetrieveAdminApiTest(TestCase):
    """
    Test suite for CourseProductRelation retrieve Admin API.
    """

    maxDiff = None

    def test_admin_api_course_products_relation_retrieve_anonymous(self):
        """
        Anonymous users should not be able to retrieve a course product relation.
        """
        relation = factories.CourseProductRelationFactory()
        response = self.client.get(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_admin_api_course_products_relation_retrieve_authenticated(self):
        """
        Authenticated users should not be able to retrieve a course product relation.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        relation = factories.CourseProductRelationFactory()
        response = self.client.get(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "You do not have permission to perform this action."},
        )

    def test_admin_api_course_products_relation_retrieve_superuser(self):
        """
        Super admin user should be able to retrieve a course product relation.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__courses=[],
        )
        response = self.client.get(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertEqual(
            response.json(),
            {
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
                    for organization in relation.organizations.all().order_by(
                        "created_on"
                    )
                ],
            },
        )
