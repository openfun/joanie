"""Test suite for the Product API"""
from djmoney.money import Money

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class ProductApiTest(BaseAPITestCase):
    """Test the API of the Product resource."""

    def test_api_product_read_list_anonymous(self):
        """
        It should not be possible to retrieve the list of products for anonymous users.
        """
        factories.ProductFactory()

        response = self.client.get("/api/v1.0/products/")

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_product_read_list_authenticated(self):
        """
        It should not be possible to retrieve the list of products for authenticated users.
        """
        factories.ProductFactory()
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        response = self.client.get(
            "/api/v1.0/products/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_product_read_detail_no_organization(self):
        """
        A product linked to a course but with no selling organization should not be returned.
        """
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        course = factories.CourseFactory()
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[]
        )

        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/products/{product.id}/?course={course.code}"
            )

        self.assertEqual(response.status_code, 404)

    def test_api_product_read_detail_with_organization_no_code(self):
        """
        Any users should not be allowed to retrieve a product if no course code is passed in
        querystring.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        organization = factories.OrganizationFactory()
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )

        with self.assertNumQueries(0):
            response = self.client.get(f"/api/v1.0/products/{product.id}/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"course": "You must specify a course code to get product details."},
        )

    def test_api_product_read_detail_with_organization_and_code(self):
        """
        Any users should be allowed to retrieve a product with minimal db access.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        organization = factories.OrganizationFactory()
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )

        with self.assertNumQueries(4):
            response = self.client.get(
                f"/api/v1.0/products/{product.id}/?course={course.code}"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "call_to_action": product.call_to_action,
                "certificate": {
                    "description": product.certificate_definition.description,
                    "name": product.certificate_definition.name,
                    "title": product.certificate_definition.title,
                },
                "organizations": [
                    {
                        "id": str(organization.id),
                        "code": organization.code,
                        "title": organization.title,
                    }
                ],
                "id": str(product.id),
                "price": float(product.price.amount),
                "price_currency": str(product.price.currency),
                "target_courses": [
                    {
                        "code": target_course.code,
                        "organization": {
                            "code": target_course.organization.code,
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
                                "enrollment_start": course_run.enrollment_start.isoformat().replace(  # noqa pylint: disable=line-too-long
                                    "+00:00", "Z"
                                ),
                                "enrollment_end": course_run.enrollment_end.isoformat().replace(  # noqa pylint: disable=line-too-long
                                    "+00:00", "Z"
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
                "title": product.title,
                "type": product.type,
                "orders": None,
            },
        )

        # Product response should have been cached,
        # so db queries should be reduced if we request the resource again.
        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/products/{product.id}/?course={course.code}"
            )

        self.assertEqual(response.status_code, 200)

        # But cache should be language sensitive
        with self.assertNumQueries(7):
            response = self.client.get(
                f"/api/v1.0/products/{product.id}/?course={course.code}",
                HTTP_ACCEPT_LANGUAGE="fr-fr",
            )

        self.assertEqual(response.status_code, 200)

    def test_api_product_detail_with_pending_order(self):
        """
        An authenticated user with a pending order related to the product resource
        should get the order id within the response
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[course], type=enums.PRODUCT_TYPE_CREDENTIAL
        )
        order = factories.OrderFactory(owner=user, product=product)

        self.assertEqual(order.state, "pending")

        with self.assertNumQueries(5):
            response = self.client.get(
                f"/api/v1.0/products/{product.id}/?course={course.code}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        content = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(content["orders"], [str(order.id)])

    def test_api_product_detail_with_validated_order(self):
        """
        An authenticated user with a validated order related to the product resource
        should get the order id within the response
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[course],
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            price=Money(0.00, "EUR"),
        )
        order = factories.OrderFactory(owner=user, product=product)

        self.assertEqual(order.state, "validated")

        with self.assertNumQueries(5):
            response = self.client.get(
                f"/api/v1.0/products/{product.id}/?course={course.code}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        content = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(content["orders"], [str(order.id)])

    def test_api_product_detail_with_cancel_order(self):
        """
        An authenticated user with a canceled order related to the product resource
        should not get the order id within the response
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[course],
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            price=Money(0.00, "EUR"),
        )
        order = factories.OrderFactory(
            owner=user, product=product, state=enums.ORDER_STATE_CANCELED
        )

        self.assertEqual(order.state, "canceled")

        with self.assertNumQueries(5):
            response = self.client.get(
                f"/api/v1.0/products/{product.id}/?course={course.code}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        content = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(content["orders"], [])

    def test_api_product_filtered_by_an_invalid_course(self):
        """
        A product can be filtered by courses. If the provided course_code does not correspond to
        a course linked to the product, a 404 response should be return.
        """
        [course1, course2] = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course1]
        )

        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/products/{product.id}/?course={course2.code}"
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not found."})

        # Link the course to the product without organizations
        product.courses.add(course2)

        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/products/{product.id}/?course={course2.code}"
            )

        content = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not found."})

        # Add an organization to the link with course2
        product.course_relations.get(course=course2).organizations.add(
            factories.OrganizationFactory()
        )

        with self.assertNumQueries(4):
            response = self.client.get(
                f"/api/v1.0/products/{product.id}/?course={course2.code}"
            )

        content = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(content["id"], str(product.id))

    def test_api_product_with_order_filtered_by_course(self):
        """
        An authenticated user who has purchased several times the same product for
        different courses should be able to filter orders property of the response
        per course.
        """
        courses = factories.CourseFactory.create_batch(2)

        # Create a certificate product linked to two courses
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            courses=courses,
            price=Money(0.00, "EUR"),
        )

        # Create a user
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        # Purchase certificate for all courses
        order1 = factories.OrderFactory(owner=user, product=product, course=courses[0])
        factories.OrderFactory(owner=user, product=product, course=courses[1])

        # If user request product only and filter to the first course,
        # it should get only one order into orders property
        with self.assertNumQueries(5):
            response = self.client.get(
                f"/api/v1.0/products/{product.id}/?course={courses[0].code}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        content = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(content["id"], str(product.id))
        self.assertListEqual(content["orders"], [str(order1.id)])

    def test_api_product_read_detail_without_course_anonymous(self):
        """
        An anonymous user should not be allowed to retrieve a product not linked to any course.
        """
        product = factories.ProductFactory(courses=[])
        response = self.client.get(f"/api/v1.0/products/{product.id}/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"course": "You must specify a course code to get product details."},
        )

    def test_api_product_read_detail_without_course_authenticated(self):
        """
        An authenticated user should not be allowed to retrieve a product
        not linked to any course.
        """
        product = factories.ProductFactory(courses=[])
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/products/{product.id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"course": "You must specify a course code to get product details."},
        )

    def test_api_product_create_anonymous(self):
        """Anonymous users should not be allowed to create a product."""
        data = {
            "type": "credential",
            "price": 1337.00,
            "price_currency": "EUR",
            "title": "A lambda product",
            "call_to_action": "Purchase now!",
        }

        response = self.client.post("/api/v1.0/products/", data=data)

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )
        self.assertEqual(models.Product.objects.count(), 0)

    def test_api_product_create_authenticated(self):
        """Authenticated users should not be allowed to create a product."""
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        data = {
            "type": "credential",
            "price": 1337.00,
            "price_currency": "EUR",
            "title": "A lambda product",
            "call_to_action": "Purchase now!",
        }

        response = self.client.post(
            "/api/v1.0/products/", data=data, HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )
        self.assertEqual(models.Product.objects.count(), 0)

    def test_api_product_update_anonymous(self):
        """Anonymous users should not be allowed to update a product."""
        product = factories.ProductFactory(price=100.0)

        data = {
            "type": "credential",
            "price": 1337.00,
            "price_currency": "EUR",
            "title": "A lambda product",
            "call_to_action": "Purchase now!",
        }

        response = self.client.put(f"/api/v1.0/products/{product.id}/", data=data)

        self.assertContains(response, 'Method \\"PUT\\" not allowed.', status_code=405)
        product.refresh_from_db()
        self.assertEqual(product.price.amount, 100.0)

    def test_api_product_update_authenticated(self):
        """Authenticated users should not be allowed to update a product."""
        product = factories.ProductFactory(price=100.0)
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        data = {
            "type": "credential",
            "price": 1337.00,
            "price_currency": "EUR",
            "title": "A lambda product",
            "call_to_action": "Purchase now!",
        }

        response = self.client.put(
            f"/api/v1.0/products/{product.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(response, 'Method \\"PUT\\" not allowed.', status_code=405)
        product.refresh_from_db()
        self.assertEqual(product.price.amount, 100.0)

    def test_api_product_partial_update_anonymous(self):
        """Anonymous users should not be allowed to partially update a product."""
        product = factories.ProductFactory(price=100.0)

        data = {"price": 1337.00}

        response = self.client.patch(f"/api/v1.0/products/{product.id}/", data=data)

        self.assertContains(
            response, 'Method \\"PATCH\\" not allowed.', status_code=405
        )
        product.refresh_from_db()
        self.assertEqual(product.price.amount, 100.0)

    def test_api_product_partial_update_authenticated(self):
        """Authenticated users should not be allowed to partially update a product."""
        product = factories.ProductFactory(price=100.0)
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        data = {
            "price": 1337.00,
        }

        response = self.client.patch(
            f"/api/v1.0/products/{product.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response, 'Method \\"PATCH\\" not allowed.', status_code=405
        )
        product.refresh_from_db()
        self.assertEqual(product.price.amount, 100.0)

    def test_api_product_delete_anonymous(self):
        """Anonymous users should not be allowed to delete a product."""
        product = factories.ProductFactory()

        response = self.client.delete(f"/api/v1.0/products/{product.id}/")

        self.assertContains(
            response, 'Method \\"DELETE\\" not allowed.', status_code=405
        )
        self.assertEqual(models.Product.objects.count(), 1)

    def test_api_product_delete_authenticated(self):
        """Authenticated users should not be allowed to delete a product."""
        product = factories.ProductFactory()
        user = factories.UserFactory.build()
        token = self.get_user_token(user.username)

        response = self.client.delete(
            f"/api/v1.0/products/{product.id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertContains(
            response, 'Method \\"DELETE\\" not allowed.', status_code=405
        )
        self.assertEqual(models.Product.objects.count(), 1)
