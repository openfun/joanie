"""Test suite for nested Order viewset on Courses"""
from http import HTTPStatus
from uuid import uuid4

from joanie.core import enums, factories
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class NestedOrderCourseViewSetAPITest(BaseAPITestCase):
    """Test suite for nested Order viewset on Courses"""

    maxDiff = None

    def test_api_courses_order_get_list_learners_anonymous_user(self):
        """
        Anonymous user should not be able to get the list learners on a given course.
        """
        course = factories.CourseFactory()

        with self.assertNumQueries(0):
            response = self.client.get(
                f"/api/v1.0/courses/{course.id}/orders/",
            )

        self.assertContains(
            response,
            "Authentication credentials were not provided.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    def test_api_courses_order_get_list_learners_authenticated_user_post_method_fails(
        self,
    ):
        """
        Authenticated user should not be able to use POST method to create a new list of orders
        for a given course.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        token = self.get_user_token(user.username)

        with self.assertNumQueries(0):
            response = self.client.post(
                f"/api/v1.0/courses/{course.id}/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"POST\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_courses_order_get_list_learners_authenticated_user_patch_method_fails(
        self,
    ):
        """
        Authenticated user should not be able to use PATCH method to update the list of orders for
        a given course.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        token = self.get_user_token(user.username)

        with self.assertNumQueries(0):
            response = self.client.patch(
                f"/api/v1.0/courses/{course.id}/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"PATCH\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_courses_order_get_list_leaners_authenticated_user_put_method_fails(
        self,
    ):
        """
        Authenticated user should not be able to use PUT method to update the list of orders for a
        given course.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        token = self.get_user_token(user.username)

        with self.assertNumQueries(0):
            response = self.client.put(
                f"/api/v1.0/courses/{course.id}/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_courses_order_get_list_learners_authenticated_user_delete_method_fails(
        self,
    ):
        """
        Authenticated user should not be able to use DELETE method to erase a list of orders for a
        given course.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        token = self.get_user_token(user.username)

        with self.assertNumQueries(0):
            response = self.client.delete(
                f"/api/v1.0/courses/{course.id}/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_courses_order_get_list_learners_filter_not_existing_course_id(
        self,
    ):
        """
        When an authenticated user parses a course 'id' that does not exist in the query params
        of the URL, it should return an empty list in return.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/courses/{uuid4()}/orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(), {"count": 0, "next": None, "previous": None, "results": []}
        )

    def test_api_courses_order_get_list_learners_when_filter_wrong_organization_query_paramaters(
        self,
    ):
        """
        When an authenticated user parses the wrong organization's 'id' in the query params
        of the URL, the user should get an empty list in return.
        """
        user = factories.UserFactory()
        user_learner = factories.UserFactory(
            email="student_do@example.fr",
            first_name="John Doe",
            username="johnDoe",
        )
        organization = factories.OrganizationFactory()
        wrong_organization = factories.OrganizationFactory()
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
        )
        factories.OrderFactory(
            organization=organization,
            owner=user_learner,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        token = self.get_user_token(user.username)

        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/courses/{relation.course.id}/orders/"
                f"?organization_id={wrong_organization.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 0)
        self.assertEqual(
            response.json(), {"count": 0, "next": None, "previous": None, "results": []}
        )

    def test_api_courses_order_get_list_learners_when_filter_not_existing_product_id(
        self,
    ):
        """
        When an authenticated user parses a course 'id' that does not exist in the query params
        of the URL, it should return an empty list in return.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/courses/{course.id}/orders/" f"?product_id={uuid4()}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(), {"count": 0, "next": None, "previous": None, "results": []}
        )

    def test_api_courses_order_get_list_learners_filter_not_existing_course_product_relation_id(
        self,
    ):
        """
        When an authenticated user parses a course product relation that does not exist in
        the query params of the URL, it should return an empty list in return.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/courses/{course.id}/orders/"
            f"?course_product_relation_id={uuid4()}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(), {"count": 0, "next": None, "previous": None, "results": []}
        )

    def test_api_courses_order_get_list_learners_authenticated_user_without_query_paramaters(
        self,
    ):
        """
        When an authenticated user parses no query params to get the list of orders on a course,
        the queryset will take the 'course_id' in the URL to filter the list. In this case where 1
        product is present in two courses, we should get 1 'validated' out of 4 orders only in
        the list in return.
        """
        user = factories.UserFactory()
        user_learners = [
            factories.UserFactory(
                email="ric_doe@example.fr", first_name="Ric Doe", username="ricDoe"
            ),
            factories.UserFactory(
                email="john_doe@example.fr", first_name="John Doe", username="johnDoe"
            ),
            factories.UserFactory(
                email="adam_doe@example.fr", first_name="Adam Doe", username="adamDoe"
            ),
            factories.UserFactory(
                email="mitsu_doe@example.fr",
                first_name="Mitsu Doe",
                username="mitsuDoe",
            ),
        ]
        organizations = factories.OrganizationFactory.create_batch(3)
        product = factories.ProductFactory()
        courses = factories.CourseFactory.create_batch(3)
        relation_1 = factories.CourseProductRelationFactory(
            product=product,
            course=courses[0],
            organizations=[organizations[0]],
        )
        relation_2 = factories.CourseProductRelationFactory(
            product=product, course=courses[1], organizations=[organizations[1]]
        )
        relation_3 = factories.CourseProductRelationFactory(
            product=product, course=courses[2], organizations=[organizations[2]]
        )
        order = factories.OrderFactory(
            owner=user_learners[0],
            product=product,
            course=relation_1.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        factories.OrderFactory(
            organization=organizations[1],
            owner=user_learners[1],
            product=product,
            course=relation_2.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        factories.OrderFactory(
            organization=organizations[1],
            owner=user_learners[2],
            product=product,
            course=relation_2.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        factories.OrderFactory(
            organization=organizations[2],
            owner=user_learners[3],
            product=product,
            course=relation_3.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        token = self.get_user_token(user.username)

        with self.assertNumQueries(24):
            response = self.client.get(
                f"/api/v1.0/courses/{relation_1.course.id}/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], str(order.id))
        self.assertEqual(response.json()["results"][0]["course_id"], str(courses[0].id))
        self.assertEqual(response.json()["results"][0]["product_id"], str(product.id))
        self.assertEqual(
            response.json()["results"][0]["owner"]["id"], str(user_learners[0].id)
        )

    def test_api_courses_order_get_list_leaners_filter_by_existing_organization_query_parameter(
        self,
    ):
        """
        Authenticated user should be able to filter out by organization the list of learners.
        He should see the order made on the course by one user who is attached to the organization.
        """
        user = factories.UserFactory()
        user_learners = [
            factories.UserFactory(
                email="student_do@example.fr", first_name="John Doe", username="johnDoe"
            ),
            factories.UserFactory(
                email="adam_doe@example.fr", first_name="Adam Doe", username="adamDoe"
            ),
        ]
        organizations = factories.OrganizationFactory.create_batch(2)
        relation = factories.CourseProductRelationFactory(
            organizations=organizations,
        )
        orders = [
            factories.OrderFactory(
                organization=organizations[i],
                owner=user_learners[i],
                product=relation.product,
                course=relation.course,
                state=enums.ORDER_STATE_VALIDATED,
            )
            for i in range(2)
        ]
        token = self.get_user_token(user.username)

        with self.assertNumQueries(24):
            response = self.client.get(
                f"/api/v1.0/courses/{relation.course.id}/orders/"
                f"?organization_id={organizations[1].id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertCountEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(orders[1].id),
                        "created_on": format_date(orders[1].created_on),
                        "organization": {
                            "id": str(organizations[1].id),
                            "code": str(organizations[1].code),
                            "logo": {
                                "filename": str(organizations[1].logo.name),
                                "height": 1,
                                "width": 1,
                                "src": f"http://testserver{organizations[1].logo.url}.1x1_q85.webp",
                                "size": organizations[1].logo.size,
                                "srcset": (
                                    f"http://testserver{organizations[1].logo.url}.1024x1024_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                                    "1024w, "
                                    f"http://testserver{organizations[1].logo.url}.512x512_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                                    "512w, "
                                    f"http://testserver{organizations[1].logo.url}.256x256_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                                    "256w, "
                                    f"http://testserver{organizations[1].logo.url}.128x128_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                                    "128w"
                                ),
                            },
                            "title": str(organizations[1].title),
                        },
                        "owner": {
                            "id": str(user_learners[1].id),
                            "username": str(user_learners[1].username),
                            "full_name": user_learners[1].get_full_name(),
                            "email": str(user_learners[1].email),
                        },
                        "course_id": str(relation.course.id),
                        "enrollment_id": None,
                        "product_id": str(relation.product.id),
                        "state": str(orders[1].state),
                    }
                ],
            },
        )

    def test_api_courses_order_get_list_filtering_filter_by_product_when_product_is_in_two_courses(
        self,
    ):
        """
        Authenticated user should get the list of orders when he parses the product's 'id' in the
        query params of the URL. When a product is present in two distinct courses, he should
        get the orders that are attached to the product's 'id' and the course's 'id'.
        """
        user = factories.UserFactory()
        user_learners = [
            factories.UserFactory(
                email="ric_doe@example.fr", first_name="Ric Doe", username="ricDoe"
            ),
            factories.UserFactory(
                email="john_doe@example.fr", first_name="John Doe", username="johnDoe"
            ),
            factories.UserFactory(
                email="adam_doe@example.fr", first_name="Adam Doe", username="adamDoe"
            ),
        ]
        organization = factories.OrganizationFactory()
        courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory()
        for course in courses:
            factories.CourseProductRelationFactory(
                product=product, course=course, organizations=[organization]
            )
        # Two orders with the same product and course
        factories.OrderFactory(
            organization=organization,
            owner=user_learners[0],
            product=product,
            course=courses[0],
            state=enums.ORDER_STATE_VALIDATED,
        )
        factories.OrderFactory(
            organization=organization,
            owner=user_learners[1],
            product=product,
            course=courses[0],
            state=enums.ORDER_STATE_VALIDATED,
        )
        # Third order with the same product and another course
        factories.OrderFactory(
            organization=organization,
            owner=user_learners[2],
            product=product,
            course=courses[1],
            state=enums.ORDER_STATE_VALIDATED,
        )
        token = self.get_user_token(user.username)

        with self.assertNumQueries(24):
            response = self.client.get(
                f"/api/v1.0/courses/{courses[0].id}/orders/"
                f"?product_id={product.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(response.json()["results"][0]["course_id"], str(courses[0].id))
        self.assertEqual(response.json()["results"][0]["product_id"], str(product.id))
        self.assertEqual(
            response.json()["results"][0]["owner"]["id"], str(user_learners[1].id)
        )
        self.assertEqual(response.json()["results"][1]["course_id"], str(courses[0].id))
        self.assertEqual(response.json()["results"][1]["product_id"], str(product.id))
        self.assertEqual(
            response.json()["results"][1]["owner"]["id"], str(user_learners[0].id)
        )

        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/courses/{courses[1].id}/orders/"
                f"?product_id={product.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["course_id"], str(courses[1].id))
        self.assertEqual(response.json()["results"][0]["product_id"], str(product.id))
        self.assertEqual(
            response.json()["results"][0]["owner"]["id"], str(user_learners[2].id)
        )

    def test_api_courses_order_get_list_learners_filter_by_product_and_organization_query_params(
        self,
    ):
        """
        Authenticated user should be able to get the list of learners by parsing the organization's
        'id' and the product's 'id' in the request's URL. The user should get in return 2 out of 3
        orders, since 2 of them are attached to the same organization.
        """
        user = factories.UserFactory()
        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory()
        user_learners = [
            factories.UserFactory(
                email="ric_doe@example.fr", first_name="Ric Doe", username="ricDoe"
            ),
            factories.UserFactory(
                email="john_doe@example.fr", first_name="John Doe", username="johnDoe"
            ),
            factories.UserFactory(
                email="adam_doe@example.fr", first_name="Adam Doe", username="adamDoe"
            ),
        ]
        for index, course in enumerate(courses, start=0):
            factories.CourseProductRelationFactory(
                product=product, course=course, organizations=[organizations[index]]
            )
        # Make Orders with product number 1 and with the common course
        factories.OrderFactory(
            organization=organizations[0],
            owner=user_learners[0],
            product=product,
            course=courses[0],
            state=enums.ORDER_STATE_VALIDATED,
        )
        factories.OrderFactory(
            organization=organizations[0],
            owner=user_learners[1],
            product=product,
            course=courses[0],
            state=enums.ORDER_STATE_VALIDATED,
        )
        # Make Order with product number 2 and with the common course
        factories.OrderFactory(
            organization=organizations[1],
            owner=user_learners[2],
            product=product,
            course=courses[1],
            state=enums.ORDER_STATE_VALIDATED,
        )
        token = self.get_user_token(user.username)

        with self.assertNumQueries(24):
            response = self.client.get(
                f"/api/v1.0/courses/{courses[0].id}/orders/"
                f"?organization_id={organizations[0].id}&product_id={product.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(response.json()["results"][0]["course_id"], str(courses[0].id))
        self.assertEqual(response.json()["results"][0]["product_id"], str(product.id))
        self.assertEqual(
            response.json()["results"][0]["organization"]["id"],
            str(organizations[0].id),
        )
        self.assertEqual(response.json()["results"][1]["course_id"], str(courses[0].id))
        self.assertEqual(response.json()["results"][1]["product_id"], str(product.id))
        self.assertEqual(
            response.json()["results"][1]["organization"]["id"],
            str(organizations[0].id),
        )

        with self.assertNumQueries(24):
            response = self.client.get(
                f"/api/v1.0/courses/{courses[1].id}/orders/"
                f"?organization_id={organizations[1].id}&product_id={product.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["course_id"], str(courses[1].id))
        self.assertEqual(response.json()["results"][0]["product_id"], str(product.id))
        self.assertEqual(
            response.json()["results"][0]["organization"]["id"],
            str(organizations[1].id),
        )

    def test_api_courses_order_get_list_learners_filter_by_course_product_relation_id_query_params(
        self,
    ):
        """
        When an authenticated user parses a course product relation 'id' in the query params,
        he should get the list of the leaners that are attached to this relation.
        """
        user = factories.UserFactory()
        product = factories.ProductFactory()
        course_1 = factories.CourseFactory()
        course_2 = factories.CourseFactory()
        organizations = factories.OrganizationFactory.create_batch(2)
        relation_1 = factories.CourseProductRelationFactory(
            product=product, course=course_1, organizations=[organizations[0]]
        )
        relation_2 = factories.CourseProductRelationFactory(
            product=product, course=course_2, organizations=[organizations[1]]
        )
        user_learners = [
            factories.UserFactory(
                email="ric_doe@example.fr", first_name="Ric Doe", username="ricDoe"
            ),
            factories.UserFactory(
                email="john_doe@example.fr", first_name="John Doe", username="johnDoe"
            ),
            factories.UserFactory(
                email="adam_doe@example.fr", first_name="Adam Doe", username="adamDoe"
            ),
        ]
        factories.OrderFactory(
            organization=organizations[0],
            owner=user_learners[0],
            product=product,
            course=relation_1.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        factories.OrderFactory(
            organization=organizations[0],
            owner=user_learners[1],
            product=product,
            course=relation_1.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        factories.OrderFactory(
            organization=organizations[1],
            owner=user_learners[2],
            product=product,
            course=relation_2.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        token = self.get_user_token(user.username)

        # should return 2 out of 3 learners
        response = self.client.get(
            f"/api/v1.0/courses/{course_1.id}/orders/"
            f"?course_product_relation_id={relation_1.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(response.json()["results"][0]["product_id"], str(product.id))
        self.assertEqual(response.json()["results"][0]["course_id"], str(course_1.id))
        self.assertEqual(response.json()["results"][1]["product_id"], str(product.id))
        self.assertEqual(response.json()["results"][1]["course_id"], str(course_1.id))

        # should return 1 out of 3 learners
        response = self.client.get(
            f"/api/v1.0/courses/{course_2.id}/orders/"
            f"?course_product_relation_id={relation_2.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["product_id"], str(product.id))
        self.assertEqual(response.json()["results"][0]["course_id"], str(course_2.id))

    def test_api_courses_order_get_list_with_course_id_not_related_to_course_product_relation_id(
        self,
    ):
        """
        When an authenticated user is parsing a course 'id' that is not related to the course
        product relation object (vice versa) he should get an empty list in return. In this case
        'course_1' is related to 'relation_1', and 'course_2' is related to 'relation_2'.
        """
        user = factories.UserFactory()
        product = factories.ProductFactory()
        course_1 = factories.CourseFactory()
        course_2 = factories.CourseFactory()
        organizations = factories.OrganizationFactory.create_batch(2)
        relation_1 = factories.CourseProductRelationFactory(
            product=product, course=course_1, organizations=[organizations[0]]
        )
        relation_2 = factories.CourseProductRelationFactory(
            product=product, course=course_2, organizations=[organizations[1]]
        )
        user_learners = [
            factories.UserFactory(
                email="ric_doe@example.fr", first_name="Ric Doe", username="ricDoe"
            ),
            factories.UserFactory(
                email="john_doe@example.fr", first_name="John Doe", username="johnDoe"
            ),
            factories.UserFactory(
                email="adam_doe@example.fr", first_name="Adam Doe", username="adamDoe"
            ),
        ]
        factories.OrderFactory(
            organization=organizations[0],
            owner=user_learners[0],
            product=product,
            course=relation_1.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        factories.OrderFactory(
            organization=organizations[0],
            owner=user_learners[1],
            product=product,
            course=relation_1.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        factories.OrderFactory(
            organization=organizations[1],
            owner=user_learners[2],
            product=product,
            course=relation_2.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/courses/{course_1.id}/orders/"
            f"?course_product_relation_id={relation_2.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 0)

        response = self.client.get(
            f"/api/v1.0/courses/{course_2.id}/orders/"
            f"?course_product_relation_id={relation_1.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 0)