"""
Test suite for CourseProductRelation update Admin API.
"""
import uuid
from unittest import mock

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories
from joanie.core.serializers import fields


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

        self.assertEqual(response.status_code, 401)
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
    def test_admin_api_course_products_relation_update_superuser(self, _):
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

        self.assertEqual(response.status_code, 200)
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
                        for target_course in (
                            product.target_courses.all().order_by(
                                "product_target_relations__position"
                            )
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

        self.assertEqual(response.status_code, 401)
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
    def test_admin_api_course_products_relation_partially_update_superuser(self, _):
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

        self.assertEqual(response.status_code, 200)
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

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_course_products_relation_partially_update_organizations(self, _):
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

        self.assertEqual(response.status_code, 200)

        assert response.json() == {
            "id": str(relation.id),
            "uri": relation.uri,
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
                        "uri": relation.uri,
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

        self.assertEqual(response.status_code, 400)

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
