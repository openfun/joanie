"""
Test suite for CourseProductRelation create Admin API.
"""
import uuid
from http import HTTPStatus
from unittest import mock

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories, models
from joanie.core.serializers import fields


class CourseProductRelationCreateAdminApiTest(TestCase):
    """
    Test suite for CourseProductRelation create Admin API.
    """

    maxDiff = None

    def test_admin_api_course_products_relation_create_anonymous(self):
        """
        Anonymous users should not be able to create a course product relation.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        organization = factories.OrganizationFactory()
        response = self.client.post(
            "/api/v1.0/admin/course-product-relations/",
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

    def test_admin_api_course_products_relation_create_authenticated(self):
        """
        Authenticated users should not be able to create a course product relation.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        organization = factories.OrganizationFactory()
        response = self.client.post(
            "/api/v1.0/admin/course-product-relations/",
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

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_course_products_relation_create_superuser(self, _):
        """
        Super admin user should be able to create a course product relation.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        organization = factories.OrganizationFactory()
        response = self.client.post(
            "/api/v1.0/admin/course-product-relations/",
            {
                "course_id": course.id,
                "product_id": product.id,
                "organization_ids": [organization.id],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        relation = models.CourseProductRelation.objects.get(id=response.json()["id"])

        self.assertDictEqual(
            response.json(),
            {
                "id": str(relation.id),
                "uri": relation.uri,
                "can_edit": relation.can_edit,
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "cover": "_this_field_is_mocked",
                    "title": course.title,
                    "organizations": [],
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
                "order_groups": [],
                "product": {
                    "id": str(product.id),
                    "title": product.title,
                    "description": product.description,
                    "call_to_action": product.call_to_action,
                    "price": float(product.price),
                    "price_currency": settings.DEFAULT_CURRENCY,
                    "type": product.type,
                    "certificate_definition": {
                        "id": str(product.certificate_definition.id),
                        "description": product.certificate_definition.description,
                        "name": product.certificate_definition.name,
                        "title": product.certificate_definition.title,
                        "template": product.certificate_definition.template,
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
                                product=product
                            ).position,
                            "is_graded": target_course.product_relations.get(
                                product=product
                            ).is_graded,
                            "title": target_course.title,
                        }
                        for target_course in product.target_courses.all().order_by(
                            "product_target_relations__position"
                        )
                    ],
                    "course_relations": [
                        {
                            "can_edit": True,
                            "course": {
                                "code": course.code,
                                "cover": "_this_field_is_mocked",
                                "id": str(course.id),
                                "organizations": [],
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
                                "title": course.title,
                            },
                            "id": str(relation.id),
                            "uri": relation.uri,
                            "order_groups": [],
                            "organizations": [
                                {
                                    "code": organization.code,
                                    "id": str(organization.id),
                                    "title": organization.title,
                                }
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
                ],
            },
        )

    def test_admin_api_course_products_relation_create_no_course_id(self):
        """
        Create a course product relation without course id should fail.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        organization = factories.OrganizationFactory()

        response = self.client.post(
            "/api/v1.0/admin/course-product-relations/",
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

    def test_admin_api_course_products_relation_create_no_product_id(self):
        """
        Create a course product relation without product id should fail.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        organization = factories.OrganizationFactory()

        response = self.client.post(
            "/api/v1.0/admin/course-product-relations/",
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

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_course_products_relation_create_no_organization_id(self, _):
        """
        Super admin user should be able to create a course product relation
        without organization id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        response = self.client.post(
            "/api/v1.0/admin/course-product-relations/",
            {
                "course_id": course.id,
                "product_id": product.id,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        relation = models.CourseProductRelation.objects.get(id=response.json()["id"])

        self.assertDictEqual(
            response.json(),
            {
                "id": str(relation.id),
                "uri": relation.uri,
                "can_edit": relation.can_edit,
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "cover": "_this_field_is_mocked",
                    "title": course.title,
                    "organizations": [],
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
                "order_groups": [],
                "product": {
                    "id": str(product.id),
                    "title": product.title,
                    "description": product.description,
                    "call_to_action": product.call_to_action,
                    "price": float(product.price),
                    "price_currency": settings.DEFAULT_CURRENCY,
                    "type": product.type,
                    "certificate_definition": {
                        "id": str(product.certificate_definition.id),
                        "description": product.certificate_definition.description,
                        "name": product.certificate_definition.name,
                        "title": product.certificate_definition.title,
                        "template": product.certificate_definition.template,
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
                                product=product
                            ).position,
                            "is_graded": target_course.product_relations.get(
                                product=product
                            ).is_graded,
                            "title": target_course.title,
                        }
                        for target_course in product.target_courses.all().order_by(
                            "product_target_relations__position"
                        )
                    ],
                    "course_relations": [
                        {
                            "can_edit": True,
                            "course": {
                                "code": course.code,
                                "cover": "_this_field_is_mocked",
                                "id": str(course.id),
                                "organizations": [],
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
                                "title": course.title,
                            },
                            "id": str(relation.id),
                            "uri": relation.uri,
                            "order_groups": [],
                            "organizations": [],
                        }
                    ],
                    "instructions": "",
                },
                "organizations": [],
            },
        )

    def test_admin_api_course_products_relation_create_no_payload(self):
        """
        Super admin user should be able to create a course product relation
        without payload.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.post(
            "/api/v1.0/admin/course-product-relations/",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "course_id": "This field is required.",
                "product_id": "This field is required.",
            },
        )

    def test_admin_api_course_products_relation_create_unknown_organization(self):
        """
        Creating a relation with unknown organization ids should fail.
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
            "/api/v1.0/admin/course-product-relations/",
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
        self.assertEqual(organization.product_relations.count(), 0)
