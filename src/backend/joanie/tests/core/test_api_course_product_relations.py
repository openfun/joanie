# pylint: disable=too-many-lines
"""Test suite for the Course Product Relation API."""
import random
import uuid
from unittest import mock

from django.conf import settings

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class CourseProductRelationApiTest(BaseAPITestCase):
    """Test the API of the CourseProductRelation resource."""

    def test_api_course_product_relation_read_list_anonymous(self):
        """
        It should not be possible to retrieve the list of course product relations for
        anonymous users.
        """
        response = self.client.get("/api/v1.0/course-product-relations/")

        self.assertEqual(response.status_code, 401)
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
        self.assertEqual(response.status_code, 200)
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
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
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
            course=course, product=product
        )
        factories.ProductFactory.create_batch(2)

        response = self.client.get(
            "/api/v1.0/course-product-relations/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
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

        self.assertEqual(response.status_code, 401)
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
        factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[courses[0]]
        )
        factories.ProductFactory.create_batch(2)

        response = self.client.get(
            f"/api/v1.0/courses/{courses[0].id}/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response.status_code, 401)

    def test_api_course_product_relation_read_detail_anonymous_with_course_id(self):
        """
        Anonymous users should get a 404 when trying to retrieve a single relation
        through a course id and a product id that does not exist.
        """
        response = self.client.get(
            f"/api/v1.0/courses/{uuid.uuid4()}/products/{uuid.uuid4()}/"
        )
        self.assertEqual(response.status_code, 404)

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
            course=course, product=product
        )

        with self.assertNumQueries(53):
            self.client.get(f"/api/v1.0/courses/{course.code}/products/{product.id}/")

        # A second call to the url should benefit from caching on the product serializer
        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/courses/{course.code}/products/{product.id}/"
            )

        self.assertEqual(response.status_code, 200)

        content = response.json()
        self.assertEqual(content["id"], str(relation.id))
        self.assertEqual(content["course"]["code"], "00000")
        self.assertEqual(content["product"]["id"], str(product.id))

        # This query should be cached
        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/courses/{course.code}/products/{product.id}/"
            )

        self.assertEqual(response.status_code, 200)

        # Then cache should be language sensitive
        with self.assertNumQueries(15):
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
            "Not found.",
            status_code=404,
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
            "Not found.",
            status_code=404,
        )

        response = self.client.get(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "Not found.",
            status_code=404,
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

        self.assertEqual(response.status_code, 404)

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
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        with self.assertNumQueries(5):
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

        self.assertEqual(response.status_code, 200)

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

        with self.assertNumQueries(51):
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

        self.assertEqual(response.status_code, 200)

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
        self.assertEqual(response.status_code, 200)

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

        self.assertEqual(response.status_code, 200)

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
        order.cancel()

        response = self.client.get(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)

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

        self.assertEqual(response.status_code, 401)
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

        self.assertContains(response, 'Method \\"POST\\" not allowed.', status_code=405)
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
            status_code=405,
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
            status_code=401,
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
            status_code=405,
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
            status_code=405,
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
            status_code=401,
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
            status_code=405,
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
            status_code=405,
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
            status_code=401,
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
            status_code=405,
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
            status_code=405,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 1)
