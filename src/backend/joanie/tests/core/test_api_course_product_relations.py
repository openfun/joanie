# pylint: disable=too-many-lines
"""Test suite for the Course Product Relation API."""

import random
import uuid
from datetime import datetime
from http import HTTPStatus
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.test import override_settings

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class CourseProductRelationApiTest(BaseAPITestCase):
    """Test the API of the CourseProductRelation resource."""

    maxDiff = None

    def test_api_course_product_relation_read_list_anonymous(self):
        """
        It should not be possible to retrieve the list of course product relations for
        anonymous users.
        """
        response = self.client.get("/api/v1.0/course-product-relations/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_course_product_relation_read_list_without_accesses(self):
        """
        It should not be possible to retrieve the list of course product relations for
        authenticated users without accesses.
        """
        factories.ProductFactory()
        user = factories.UserFactory.build()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/course-product-relations/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(
            content,
            {
                "count": 0,
                "results": [],
                "previous": None,
                "next": None,
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_course_product_relation_read_list_with_accesses(self, _):
        """
        An authenticated user should be able to list all course product relations
        related to courses for which it has accesses.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        courses = factories.CourseFactory.create_batch(2)
        for course in courses:
            factories.UserCourseAccessFactory(user=user, course=course)
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            contract_definition=factories.ContractDefinitionFactory(),
        )
        product.instructions = (
            "# An h1 header\n"
            "Paragraphs are separated by a blank line.\n"
            "2nd paragraph. *Italic*, **bold**, and `monospace`.\n"
            "Itemized lists look like:\n"
            "* this one\n"
            "* that one\n"
            "&gt; Block quotes\n"
            "## An h2 header\n"
            "1. first item\n"
            "2. second item\n"
        )
        product.save()
        course = courses[0]
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        factories.ProductFactory.create_batch(2)

        response = self.client.get(
            "/api/v1.0/course-product-relations/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(
            content["results"][0],
            {
                "id": str(relation.id),
                "created_on": relation.created_on.isoformat().replace("+00:00", "Z"),
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "cover": "_this_field_is_mocked",
                    "title": course.title,
                },
                "order_groups": [],
                "product": {
                    "instructions": (
                        "<h1>An h1 header</h1>\n"
                        "<p>Paragraphs are separated by a blank line.\n"
                        "2nd paragraph. <em>Italic</em>, <strong>bold</strong>, "
                        "and <code>monospace</code>.\n"
                        "Itemized lists look like:\n"
                        "* this one\n"
                        "* that one\n"
                        "&gt; Block quotes</p>\n"
                        "<h2>An h2 header</h2>\n"
                        "<ol>\n"
                        "<li>first item</li>\n"
                        "<li>second item</li>\n"
                        "</ol>"
                    ),
                    "call_to_action": relation.product.call_to_action,
                    "certificate_definition": {
                        "description": relation.product.certificate_definition.description,
                        "name": relation.product.certificate_definition.name,
                        "title": relation.product.certificate_definition.title,
                    },
                    "contract_definition": {
                        "id": str(product.contract_definition.id),
                        "description": product.contract_definition.description,
                        "language": product.contract_definition.language,
                        "title": product.contract_definition.title,
                    },
                    "state": {
                        "priority": product.state["priority"],
                        "datetime": product.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if product.state["datetime"]
                        else None,
                        "call_to_action": product.state["call_to_action"],
                        "text": product.state["text"],
                    },
                    "id": str(relation.product.id),
                    "price": float(relation.product.price),
                    "price_currency": settings.DEFAULT_CURRENCY,
                    "target_courses": [
                        {
                            "code": target_course.code,
                            "organization": {
                                "id": str(target_course.organization.id),
                                "code": target_course.organization.code,
                                "logo": "_this_field_is_mocked",
                                "title": target_course.organization.title,
                            },
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
                                    "enrollment_start": course_run.enrollment_start.isoformat().replace(  # pylint: disable=line-too-long
                                        "+00:00",
                                        "Z",
                                    ),
                                    "enrollment_end": course_run.enrollment_end.isoformat().replace(  # pylint: disable=line-too-long
                                        "+00:00",
                                        "Z",
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
                        for target_course in relation.product.target_courses.all().order_by(
                            "product_target_relations__position"
                        )
                    ],
                    "title": relation.product.title,
                    "type": relation.product.type,
                },
                "organizations": [
                    {
                        "code": organization.code,
                        "id": str(organization.id),
                        "logo": "_this_field_is_mocked",
                        "title": organization.title,
                        "address": None,
                        "enterprise_code": organization.enterprise_code,
                        "activity_category_code": (organization.activity_category_code),
                        "contact_email": organization.contact_email,
                        "contact_phone": organization.contact_phone,
                        "dpo_email": organization.dpo_email,
                    }
                    for organization in relation.organizations.all()
                ],
            },
        )

    def test_api_course_product_relation_read_list_filtered_by_course_anonymous(self):
        """
        It should not be possible to list course's product relations for
        anonymous users.
        """
        course = factories.CourseFactory()
        response = self.client.get(f"/api/v1.0/courses/{course.id}/products/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_course_product_relation_read_list_filtered_by_course_with_accesses(
        self, _
    ):
        """
        An authenticated user should be able to list all course's product relations
        for which it has accesses
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        courses = factories.CourseFactory.create_batch(2)
        for course in courses:
            factories.UserCourseAccessFactory(user=user, course=course)
        factories.CourseProductRelationFactory(
            product=factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
            ),
            course=courses[0],
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        factories.ProductFactory.create_batch(2)

        response = self.client.get(
            f"/api/v1.0/courses/{courses[0].id}/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)

    def test_api_course_product_relation_read_list_filtered_by_course_without_accesses(
        self,
    ):
        """
        It should not be possible to list course's product relations for
        authenticated users without accesses.
        """
        factories.ProductFactory()
        course = factories.CourseFactory()
        user = factories.UserFactory.build()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/courses/{course.id}/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(
            content,
            {
                "count": 0,
                "results": [],
                "previous": None,
                "next": None,
            },
        )

    def test_api_course_product_relation_read_list_filtered_by_product_type(self):
        """
        An authenticated user should be able to list all course's product relations
        filtered by product type.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            factories.CourseProductRelationFactory(
                product=factories.ProductFactory(type=product_type, courses=[]),
                course=access.course,
                organizations=factories.OrganizationFactory.create_batch(1),
            )

        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 3)

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            response = self.client.get(
                f"/api/v1.0/courses/{access.course.id}/products/?product_type={product_type}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(len(content["results"]), 1)

        # Test with multiple product types
        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/"
            "?product_type=credential"
            "&product_type=certificate",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 2)

    def test_api_course_product_relation_read_list_filtered_by_invalid_product_type(
        self,
    ):
        """
        An authenticated user should be able to list all course's product relations
        filtered by product type but if the type is invalid, it should
        return a 400.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)

        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/?product_type=invalid",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            '{"product_type":['
            '"Select a valid choice. invalid is not one of the available choices."'
            "]}",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_course_product_relation_read_list_filtered_by_excluded_product_type(
        self,
    ):
        """
        An authenticated user should be able to list all course's product relations
        filtered by excluding product type.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            factories.CourseProductRelationFactory(
                product=factories.ProductFactory(type=product_type, courses=[]),
                course=access.course,
                organizations=factories.OrganizationFactory.create_batch(1),
            )

        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 3)

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            response = self.client.get(
                f"/api/v1.0/courses/{access.course.id}/products/"
                f"?product_type_exclude={product_type}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(len(content["results"]), 2)

        # Test with multiple excluded product types
        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/"
            "?product_type_exclude=credential"
            "&product_type_exclude=certificate",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)

    def test_api_course_product_relation_read_list_filtered_by_invalid_excluded_product_type(
        self,
    ):
        """
        An authenticated user should be able to list all course's product relations
        filtered by excluded product type but if the type is invalid, it should
        return a 400.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)

        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/?product_type_exclude=invalid",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            '{"product_type_exclude":['
            '"Select a valid choice. invalid is not one of the available choices."'
            "]}",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_course_product_relation_read_detail_anonymous(self):
        """
        Anonymous users should not be able to retrieve a single relation through its id.
        """
        courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=courses
        )
        relation = models.CourseProductRelation.objects.get(
            course=courses[0], product=product
        )

        response = self.client.get(f"/api/v1.0/course-product-relations/{relation.id}/")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_course_product_relation_read_detail_anonymous_with_course_id(self):
        """
        Anonymous users should get a 404 when trying to retrieve a single relation
        through a course id and a product id that does not exist.
        """
        response = self.client.get(
            f"/api/v1.0/courses/{uuid.uuid4()}/products/{uuid.uuid4()}/"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_course_product_relation_read_detail_with_product_id_anonymous(self):
        """
        Anonymous users should be able to retrieve a single course product relation
        if a product id is provided.
        """
        course = factories.CourseFactory(code="00000")
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=factories.CourseFactory.create_batch(2),
        )
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )

        with self.assertNumQueries(77):
            self.client.get(f"/api/v1.0/courses/{course.code}/products/{product.id}/")

        # A second call to the url should benefit from caching on the product serializer
        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/courses/{course.code}/products/{product.id}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(content["id"], str(relation.id))
        self.assertEqual(content["course"]["code"], "00000")
        self.assertEqual(content["product"]["id"], str(product.id))

        # This query should be cached
        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/courses/{course.code}/products/{product.id}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Then cache should be language sensitive
        with self.assertNumQueries(18):
            self.client.get(
                f"/api/v1.0/courses/{course.code}/products/{product.id}/",
                HTTP_ACCEPT_LANGUAGE="fr-fr",
            )

        with self.assertNumQueries(2):
            self.client.get(
                f"/api/v1.0/courses/{course.code}/products/{product.id}/",
                HTTP_ACCEPT_LANGUAGE="fr-fr",
            )

    def test_api_course_product_relation_read_detail_no_organization(self):
        """
        A course product relation without organizations should not be returned.
        """
        relation = factories.CourseProductRelationFactory(
            organizations=[],
        )

        # Anonymous user should not be able to retrieve this relation
        response = self.client.get(
            f"/api/v1.0/courses/{relation.course.id}/products/{relation.product.id}/",
        )
        self.assertContains(
            response,
            "No CourseProductRelation matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

        # Authenticated user with course access should not be able
        # to retrieve this relation
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.UserCourseAccessFactory(
            user=user,
            course=relation.course,
        )

        response = self.client.get(
            f"/api/v1.0/courses/{relation.course.id}/products/{relation.product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "No CourseProductRelation matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

        response = self.client.get(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "No CourseProductRelation matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_api_course_product_relation_read_detail_without_accesses(self):
        """
        Authenticated users without course access should not be able to retrieve
        a single course product relation through its id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )

        response = self.client.get(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_course_product_relation_read_detail_with_accesses(self, _):
        """
        Authenticated users with course access should be able to retrieve
        a single course product relation through its id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        relation = factories.CourseProductRelationFactory(
            course=course,
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        with self.assertNumQueries(6):
            self.client.get(
                f"/api/v1.0/course-product-relations/{relation.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        # A second call to the url should benefit from caching on the product serializer
        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/course-product-relations/{relation.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content,
            {
                "id": str(relation.id),
                "created_on": relation.created_on.isoformat().replace("+00:00", "Z"),
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "cover": "_this_field_is_mocked",
                    "title": course.title,
                },
                "order_groups": [],
                "product": {
                    "instructions": "",
                    "call_to_action": relation.product.call_to_action,
                    "certificate_definition": {
                        "description": relation.product.certificate_definition.description,
                        "name": relation.product.certificate_definition.name,
                        "title": relation.product.certificate_definition.title,
                    },
                    "contract_definition": {
                        "id": str(relation.product.contract_definition.id),
                        "description": relation.product.contract_definition.description,
                        "language": relation.product.contract_definition.language,
                        "title": relation.product.contract_definition.title,
                    },
                    "state": {
                        "priority": relation.product.state["priority"],
                        "datetime": relation.product.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if relation.product.state["datetime"]
                        else None,
                        "call_to_action": relation.product.state["call_to_action"],
                        "text": relation.product.state["text"],
                    },
                    "id": str(relation.product.id),
                    "price": float(relation.product.price),
                    "price_currency": settings.DEFAULT_CURRENCY,
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
                                    "enrollment_start": course_run.enrollment_start.isoformat().replace(  # pylint: disable=line-too-long
                                        "+00:00",
                                        "Z",
                                    ),
                                    "enrollment_end": course_run.enrollment_end.isoformat().replace(  # pylint: disable=line-too-long
                                        "+00:00",
                                        "Z",
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
                        for target_course in relation.product.target_courses.all().order_by(
                            "product_target_relations__position"
                        )
                    ],
                    "title": relation.product.title,
                    "type": relation.product.type,
                },
                "organizations": [
                    {
                        "code": organization.code,
                        "id": str(organization.id),
                        "logo": "_this_field_is_mocked",
                        "title": organization.title,
                        "address": None,
                        "enterprise_code": organization.enterprise_code,
                        "activity_category_code": (organization.activity_category_code),
                        "contact_email": organization.contact_email,
                        "contact_phone": organization.contact_phone,
                        "dpo_email": organization.dpo_email,
                    }
                    for organization in relation.organizations.all()
                ],
            },
        )

    def test_api_course_product_relation_read_detail_with_order_groups(self):
        """The detail of order groups related to the product should be served as expected."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        relation = factories.CourseProductRelationFactory()
        product = relation.product
        course = relation.course
        factories.UserCourseAccessFactory(user=user, course=course)
        order_group1 = factories.OrderGroupFactory(
            course_product_relation=relation, nb_seats=random.randint(10, 100)
        )
        order_group2 = factories.OrderGroupFactory(course_product_relation=relation)
        binding_states = ["pending", "submitted", "validated"]
        for _ in range(3):
            factories.OrderFactory(
                course=course,
                product=product,
                order_group=order_group1,
                state=random.choice(binding_states),
            )
        for state, _label in enums.ORDER_STATE_CHOICES:
            if state in binding_states:
                continue
            factories.OrderFactory(
                course=course, product=product, order_group=order_group1, state=state
            )

        with self.assertNumQueries(52):
            self.client.get(
                f"/api/v1.0/course-product-relations/{relation.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        # A second call to the url should benefit from caching on
        # the course product relation serializer
        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/course-product-relations/{relation.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content["order_groups"],
            [
                {
                    "id": str(order_group1.id),
                    "is_active": True,
                    "nb_available_seats": order_group1.nb_seats - 3,
                    "nb_seats": order_group1.nb_seats,
                },
                {
                    "id": str(order_group2.id),
                    "is_active": True,
                    "nb_available_seats": order_group2.nb_seats,
                    "nb_seats": order_group2.nb_seats,
                },
            ],
        )

    def test_api_course_product_relation_read_detail_with_order_groups_cache(self):
        """Cache should be reset on order submit and cancel."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        product = factories.ProductFactory(price="0.00")
        relation = factories.CourseProductRelationFactory(product=product)
        factories.UserCourseAccessFactory(user=user, course=relation.course)
        order_group = factories.OrderGroupFactory(
            course_product_relation=relation, nb_seats=10
        )
        order = factories.OrderFactory(
            product=product, course=relation.course, order_group=order_group
        )

        response = self.client.get(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content["order_groups"],
            [
                {
                    "id": str(order_group.id),
                    "is_active": True,
                    "nb_available_seats": 10,
                    "nb_seats": 10,
                },
            ],
        )

        # Submitting order should impact the number of seat availabilities in the
        # representation of the product
        order.submit()

        response = self.client.get(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertEqual(
            response.json()["order_groups"],
            [
                {
                    "id": str(order_group.id),
                    "is_active": True,
                    "nb_available_seats": 9,
                    "nb_seats": 10,
                },
            ],
        )

        # Cancelling order should re-credit the number of seat availabilities in the
        # representation of the product
        order.flow.cancel()

        response = self.client.get(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertEqual(
            response.json()["order_groups"],
            [
                {
                    "id": str(order_group.id),
                    "is_active": True,
                    "nb_available_seats": 10,
                    "nb_seats": 10,
                },
            ],
        )

    def test_api_course_product_relation_create_anonymous(self):
        """
        Anonymous users should not be able to create a course product relation.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )

        response = self.client.post(
            "/api/v1.0/courses/products/",
            data={
                "course_id": str(course.id),
                "product_id": str(product.id),
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 0)

    def test_api_course_product_relation_create_authenticated(self):
        """
        Authenticated users should not be able to
        create a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )

        response = self.client.post(
            "/api/v1.0/courses/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course_id": str(course.id),
                "product_id": str(product.id),
            },
        )

        self.assertContains(
            response,
            'Method \\"POST\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 0)

    def test_api_course_product_relation_create_with_accesses(self):
        """
        Authenticated users with course access should not be able
        to create a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.post(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course_id": str(course.id),
                "product_id": str(product.id),
            },
        )

        self.assertContains(
            response,
            'Method \\"POST\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_course_product_relation_update_anonymous(self):
        """
        Anonymous users should not be able to update a course product relation.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.put(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            data={
                "course_id": "abc",
                "product_id": "def",
            },
        )

        self.assertContains(
            response,
            "Authentication credentials were not provided.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    def test_api_course_product_relation_update_authenticated(self):
        """
        Authenticated users without course access should not be able to
        update a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.put(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course_id": str(course.id),
                "product_id": str(product.id),
            },
        )

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_course_product_relation_update_with_accesses(self):
        """
        Authenticated users with course access should not be able
        to update a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.put(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course_id": str(course.id),
                "product_id": str(product.id),
            },
        )

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_course_product_relation_partially_update_anonymous(self):
        """
        Anonymous users should not be able to partially update a course product relation.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.patch(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            data={
                "product_id": "def",
            },
        )

        self.assertContains(
            response,
            "Authentication credentials were not provided.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    def test_api_course_product_relation_partially_update_authenticated(self):
        """
        Authenticated users without course access should not be able to
        partially update a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.patch(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "product_id": "def",
            },
        )

        self.assertContains(
            response,
            'Method \\"PATCH\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_course_product_relation_partially_update_with_accesses(self):
        """
        Authenticated users with course access should not be able to
        partially update a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.patch(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "product_id": "def",
            },
        )

        self.assertContains(
            response,
            'Method \\"PATCH\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_course_product_relation_delete_anonymous(self):
        """
        Anonymous users should not be able to delete a course product relation.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.delete(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/"
        )

        self.assertContains(
            response,
            "Authentication credentials were not provided.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 1)

    def test_api_course_product_relation_delete_authenticated(self):
        """
        Authenticated users without course access should not be able to
        delete a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.delete(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 1)

    def test_api_course_product_relation_delete_with_access(self):
        """
        Authenticated users with course access should not be able to
        delete a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.delete(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 1)

    def test_api_course_product_relation_read_list_filtered_by_product_title(self):
        """
        An authenticated user should be able to filter course product relation by
        product title.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)
        organization = factories.OrganizationFactory()
        product_1 = factories.ProductFactory(
            title="Introduction to resource filtering", courses=[]
        )
        product_2 = factories.ProductFactory(
            title="Advanced aerodynamic flows", courses=[]
        )
        product_3 = factories.ProductFactory(
            title="Rubber management on a single-seater", courses=[]
        )
        # Create translations title for products
        product_1.translations.create(
            language_code="fr-fr", title="Introduction au filtrage de resource"
        )
        product_2.translations.create(
            language_code="fr-fr", title="Flux aérodynamiques avancés"
        )
        product_3.translations.create(
            language_code="fr-fr", title="Gestion d'une gomme sur une monoplace"
        )
        for product in [product_1, product_3]:
            factories.CourseProductRelationFactory(
                organizations=[organization], product=product
            )

        course_product_relation = factories.CourseProductRelationFactory(
            product=product_2,
            course=access.course,
            organizations=[organization],
        )

        # Prepare queries to test
        queries = [
            "Flux aérodynamiques avancés",
            "Flux+aérodynamiques+avancés",
            "aérodynamiques",
            "aerodynamic",
            "aéro",
            "aero",
            "aer",
            "advanced",
            "flows",
            "flo",
            "Advanced aerodynamic flows",
            "adv",
            "dynamic",
            "dyn",
            "ows",
            "av",
            "ux",
        ]

        for query in queries:
            response = self.client.get(
                f"/api/v1.0/course-product-relations/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(len(content["results"]), 1)
            self.assertEqual(
                content["results"][0].get("id"), str(course_product_relation.id)
            )

        # without parsing a query in parameter
        response = self.client.get(
            "/api/v1.0/course-product-relations/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["count"], 1)
        self.assertEqual(
            content["results"][0].get("id"), str(course_product_relation.id)
        )

        # with parsing a fake product title as query parameter
        response = self.client.get(
            "/api/v1.0/course-product-relations/?query=veryFakeProductTitle",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_course_product_relation_read_list_filtered_by_course_code(self):
        """
        An authenticated user should be able to filter course product relation by
        course code.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        course_1 = factories.CourseFactory(
            title="Introduction to resource filtering", code="MYCODE-0990"
        )
        course_2 = factories.CourseFactory(
            title="Advanced aerodynamic flows", code="MYCODE-0991"
        )
        course_3 = factories.CourseFactory(
            title="Rubber management on a single-seater", code="MYCODE-0992"
        )
        access = factories.UserCourseAccessFactory(user=user, course=course_2)
        course_product_relation = factories.CourseProductRelationFactory(
            course=access.course,
            organizations=[organization],
        )
        for course in [course_1, course_3]:
            factories.CourseProductRelationFactory(
                organizations=[organization], course=course
            )

        response = self.client.get(
            f"/api/v1.0/course-product-relations/?query={access.course.code}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(
            content["results"][0].get("id"), str(course_product_relation.id)
        )

        response = self.client.get(
            f"/api/v1.0/course-product-relations/?query={access.course.code[:1]}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(
            content["results"][0].get("id"), str(course_product_relation.id)
        )

        # without parsing a query parameter I should see my course product relation
        response = self.client.get(
            "/api/v1.0/course-product-relations/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(
            content["results"][0].get("id"), str(course_product_relation.id)
        )

        # with parsing a fake product title as query parameter
        response = self.client.get(
            "/api/v1.0/course-product-relations/?query=veryFakeCourseCode",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_course_product_relation_read_list_filtered_by_organization_title(self):
        """
        An authenticated user should be able to filter course product relation by
        organization title when they have access to the course.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)
        organization_1 = factories.OrganizationFactory(title="Organization alpha 01")
        organization_2 = factories.OrganizationFactory(title="Organization beta 02")
        organization_3 = factories.OrganizationFactory(title="Organization kappa 03")
        organization_4 = factories.OrganizationFactory(title="Organization gamma 04")
        for organization in [organization_1, organization_2, organization_3]:
            factories.CourseProductRelationFactory(organizations=[organization])
        course_product_relation = factories.CourseProductRelationFactory(
            course=access.course,
            organizations=[organization_4],
        )

        # Prepare queries to test
        queries = [
            "amma",
            "gamma",
            "mm",
            "or",
            "organ",
            "organization",
            "organization g",
            "organization+ga",
            "organization gamma",
            "04",
            "ma 04",
        ]

        for query in queries:
            response = self.client.get(
                f"/api/v1.0/course-product-relations/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(len(content["results"]), 1)
            self.assertEqual(
                content["results"][0].get("id"), str(course_product_relation.id)
            )

        # without parsing a query in parameter
        response = self.client.get(
            "/api/v1.0/course-product-relations/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["count"], 1)
        self.assertEqual(
            content["results"][0].get("id"), str(course_product_relation.id)
        )

        # with parsing a fake product title as query parameter
        response = self.client.get(
            "/api/v1.0/course-product-relations/?query=veryFakeOrganizationTitle",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            5: (30, 70),
            10: (30, 45, 45),
            100: (20, 30, 30, 20),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_course_product_relation_payment_schedule_with_product_id_anonymous(
        self,
    ):
        """
        Anonymous users should be able to retrieve a payment schedule for
        a single course product relation if a product id is provided.
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        product = factories.ProductFactory(
            price=3,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        relation = factories.CourseProductRelationFactory(
            course=course_run.course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch(
                "django.utils.timezone.now",
                return_value=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            ),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-schedule/"
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/course-product-relations/{relation.id}/payment-schedule/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "amount": 0.90,
                    "currency": settings.DEFAULT_CURRENCY,
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "amount": 2.10,
                    "currency": settings.DEFAULT_CURRENCY,
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        self.assertEqual(response_relation_path.status_code, HTTPStatus.OK)
        self.assertEqual(response_relation_path.json(), response.json())
