"""
Test suite for CourseProductRelation retrieve Admin API.
"""
from unittest import mock

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories
from joanie.core.serializers import fields


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

        self.assertEqual(response.status_code, 401)
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

        self.assertEqual(response.status_code, 403)
        self.assertDictEqual(
            response.json(),
            {"detail": "You do not have permission to perform this action."},
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_course_products_relation_retrieve_superuser(self, _):
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

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json(),
            {
                "id": str(relation.id),
                "can_edit": relation.can_edit,
                "course": {
                    "code": relation.course.code,
                    "id": str(relation.course.id),
                    "cover": "_this_field_is_mocked",
                    "title": relation.course.title,
                    "organizations": [],
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
                "order_groups": [],
                "product": {
                    "id": str(relation.product.id),
                    "title": relation.product.title,
                    "description": relation.product.description,
                    "call_to_action": relation.product.call_to_action,
                    "price": float(relation.product.price),
                    "price_currency": settings.DEFAULT_CURRENCY,
                    "type": relation.product.type,
                    "certificate_definition": {
                        "id": str(relation.product.certificate_definition.id),
                        "description": relation.product.certificate_definition.description,
                        "name": relation.product.certificate_definition.name,
                        "title": relation.product.certificate_definition.title,
                        "template": relation.product.certificate_definition.template,
                    },
                    "target_courses": [
                        {
                            "code": target_course.code,
                            "course_runs": [
                                {
                                    "id": course_run.id,
                                    "title": course_run.title,
                                    "resource_link": course_run.resource_link,
                                    "state": {
                                        "priority": course_run.state["priority"],
                                        "datetime": course_run.state["datetime"]
                                        .isoformat()
                                        .replace("+00:00", "Z"),
                                        "call_to_action": course_run.state[
                                            "call_to_action"
                                        ],
                                        "text": course_run.state["text"],
                                    },
                                    "start": course_run.start.isoformat().replace(
                                        "+00:00", "Z"
                                    ),
                                    "end": course_run.end.isoformat().replace(
                                        "+00:00", "Z"
                                    ),
                                    "enrollment_start": (
                                        course_run.enrollment_start.isoformat().replace(
                                            "+00:00", "Z"
                                        )
                                    ),
                                    "enrollment_end": (
                                        course_run.enrollment_end.isoformat().replace(
                                            "+00:00", "Z"
                                        )
                                    ),
                                }
                                for course_run in target_course.course_runs.all().order_by(
                                    "start"
                                )
                            ],
                            "position": target_course.product_relations.get(
                                product=relation.product
                            ).position,
                            "is_graded": target_course.product_relations.get(
                                product=relation.product
                            ).is_graded,
                            "title": target_course.title,
                        }
                        for target_course in (
                            relation.product.target_courses.all().order_by(
                                "product_target_relations__position"
                            )
                        )
                    ],
                    "course_relations": [
                        {
                            "can_edit": True,
                            "course": {
                                "code": relation.course.code,
                                "cover": "_this_field_is_mocked",
                                "id": str(relation.course.id),
                                "organizations": [],
                                "state": {
                                    "priority": relation.course.state["priority"],
                                    "datetime": relation.course.state["datetime"]
                                    .isoformat()
                                    .replace("+00:00", "Z")
                                    if relation.course.state["datetime"]
                                    else None,
                                    "call_to_action": relation.course.state[
                                        "call_to_action"
                                    ],
                                    "text": relation.course.state["text"],
                                },
                                "title": relation.course.title,
                            },
                            "id": str(relation.id),
                            "order_groups": [],
                            "organizations": [
                                {
                                    "code": organization.code,
                                    "id": str(organization.id),
                                    "title": organization.title,
                                }
                                for organization in relation.organizations.all()
                            ],
                        }
                    ],
                    "instructions": "",
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
