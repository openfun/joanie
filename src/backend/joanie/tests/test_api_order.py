"""
Test suite for orders API
"""
import json

from django.test.utils import override_settings
from django.utils import translation

import arrow

from joanie.core import enums, factories, models

from .base import BaseAPITestCase

OPENEDX_COURSE_RUN_URI = "http://openedx.test/courses/course-v1:edx+001+{:s}/course"


# pylint: disable=too-many-instance-attributes,attribute-defined-outside-init
class OrderAPITestCase(BaseAPITestCase):
    """Test suite for API to manipulate orders."""

    def setUp(self):
        """
        We are testing in english
        """
        super().setUp()
        translation.activate("en-us")

    def test_get_products_available_for_a_course(self):
        """
        Just check that we can get all products available for a course.
        No authentication or permission is needed.
        """
        course = factories.CourseFactory()
        products = factories.ProductFactory.create_batch(2, course=course)

        # Add 2 course runs for each product
        relation11, relation12 = factories.ProductCourseRelationFactory.create_batch(
            2,
            product=products[0],
        )
        relation21, relation22 = factories.ProductCourseRelationFactory.create_batch(
            2,
            product=products[1],
        )
        # Add a third course run with the same position as the first course run
        # for each product to test ordering by start date as second criteria
        factories.ProductCourseRelationFactory(
            product=products[0], position=relation11.position
        )
        factories.ProductCourseRelationFactory(
            product=products[1], position=relation21.position
        )

        # Get all products available for the course
        with self.assertNumQueries(
            1  # select course
            + 1  # select product
            + 2  # select course run positions x 2 products
        ):
            response = self.client.get(f"/api/courses/{course.code}/products")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        # Two products are available
        self.assertEqual(len(content), 2)
        for p, product in enumerate(reversed(products)):
            self.assertEqual(content[p]["id"], str(product.uid))
            self.assertEqual(
                content[p]["title"],
                product.title,
            )
            self.assertEqual(
                content[p]["call_to_action"],
                product.call_to_action,
            )
            self.assertEqual(
                int(content[p]["price"]),
                product.price,
            )

            # 3 sessions are available for each product
            self.assertEqual(len(content[p]["course_runs"]), 3)

            # check course run details returned
            for cr in range(3):
                # check ordering by position then start date
                if cr > 0:
                    self.assertLessEqual(
                        content[p]["course_runs"][cr - 1]["position"],
                        content[p]["course_runs"][cr]["position"],
                    )
                    if (
                        content[p]["course_runs"][cr - 1]["position"]
                        == content[p]["course_runs"][cr]["position"]
                    ):
                        self.assertLessEqual(
                            content[p]["course_runs"][cr - 1]["start"],
                            content[p]["course_runs"][cr]["start"],
                        )

            self.assertCountEqual(
                [content[p]["course_runs"][cr]["position"] for cr in range(3)],
                list(
                    models.ProductCourseRelation.objects.filter(
                        product=product
                    ).values_list("position", flat=True)
                ),
            )
            self.assertCountEqual(
                [content[p]["course_runs"][cr]["resource_link"] for cr in range(3)],
                list(
                    models.CourseRun.objects.filter(
                        product_relations__product=product
                    ).values_list("resource_link", flat=True)
                ),
            )
            for field in ["start", "end", "enrollment_start", "enrollment_end"]:
                self.assertCountEqual(
                    [content[p]["course_runs"][cr][field][:-6] for cr in range(3)],
                    [
                        "{:%Y-%m-%d %H:%M:%S}".format(getattr(cr, field))
                        for cr in models.CourseRun.objects.filter(
                            product_relations__product=product
                        )
                    ],
                )

    def test_api_order_post_without_authorization(self):
        """Order creation not allowed without HTTP AUTH"""
        relation = factories.ProductCourseRelationFactory()

        # Try to set order without Authorization
        response = self.client.post(
            "/api/orders/",
            data={
                "id": relation.product.uid,
                "resource_links": [
                    relation.course_run.resource_link,
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_post_with_bad_token(self):
        """Order creation not allowed with bad user token"""
        relation = factories.ProductCourseRelationFactory()

        # Try to set order with bad token
        response = self.client.post(
            "/api/orders/",
            data={
                "id": relation.product.uid,
                "resource_links": [
                    relation.course_run.resource_link,
                ],
            },
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer nawak",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_order_post_with_expired_token(self):
        """Order creation not allowed with user token expired"""
        relation = factories.ProductCourseRelationFactory()

        # Try to set order with expired token
        token = self.get_user_token(
            "panoramix",
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.post(
            "/api/orders/",
            data={
                "id": relation.product.uid,
                "resource_links": [
                    relation.course_run.resource_link,
                ],
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.failing.FailingLMSBackend",
                "BASE_URL": "http://openedx.test",
                "SELECTOR_REGEX": r".*openedx.test.*",
                "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            },
        ]
    )
    def test_api_order_post_lms_broken_lms(self):
        """
        Test order creation with broken lms
        """
        relation = factories.ProductCourseRelationFactory(
            course_run__resource_link=OPENEDX_COURSE_RUN_URI.format("001")
        )
        factories.ProductCourseRelationFactory(
            product=relation.product,
            course_run__resource_link=OPENEDX_COURSE_RUN_URI.format("002"),
        )

        # Set an order for the course to a new user Panoramix
        self.assertEqual(models.User.objects.count(), 0)

        username = "panoramix"

        # we call api with a valid token
        token = self.get_user_token(username)

        with self.assertLogs(level="ERROR") as logs:
            response = self.client.post(
                "/api/orders/",
                data={
                    "id": relation.product.uid,
                    "resource_links": [
                        relation.course_run.resource_link,
                    ],
                },
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertIn("Internal server error", logs.output[0])
        self.assertEqual(response.status_code, 200)

        # panoramix was a unknown user, so a new user was created
        self.assertEqual(models.User.objects.get().username, username)

        # an order was created at failed state
        order = models.Order.objects.get()
        self.assertEqual(order.state, enums.ORDER_STATE_FAILED)
        self.assertEqual(order.enrollments.count(), 2)
        self.assertEqual(
            set(order.enrollments.values_list("state", flat=True)),
            {enums.ENROLLMENT_STATE_FAILED},
        )

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
                "BASE_URL": "http://openedx.test",
                "SELECTOR_REGEX": r".*openedx.test.*",
                "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            },
        ]
    )
    def test_api_order_post(self):
        """
        Order creation is allowed with a valid user token given
        and valid data about the product and its course runs selected
        """
        course_run1 = factories.CourseRunFactory(
            resource_link=OPENEDX_COURSE_RUN_URI.format("001")
        )
        relation1 = factories.ProductCourseRelationFactory(course=course_run1.course)
        course_run2 = factories.CourseRunFactory(
            resource_link=OPENEDX_COURSE_RUN_URI.format("002")
        )
        relation2 = factories.ProductCourseRelationFactory(
            product=relation1.product, course=course_run2.course
        )
        # Set an order for the botany course to a new user Panoramix
        self.assertEqual(models.User.objects.count(), 0)

        username = "panoramix"

        # We call api with a valid token
        token = self.get_user_token(username)
        response = self.client.post(
            "/api/orders/",
            data={
                "product": relation1.product.uid,
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        content = json.loads(response.content)
        print(content)
        self.assertEqual(response.status_code, 200)
        # Panoramix was a unknown user, so a new user was created
        self.assertEqual(models.User.objects.get().username, username)

        # An order was created at pending state
        order = models.Order.objects.get()
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)
        # The 2 course runs selected were linked to the order
        self.assertEqual(order.courses.count(), 2)
        # An enrollment was created for each course run with a state set to 'in progress'
        self.assertEqual(models.Enrollment.objects.count(), 2)
        self.assertEqual(
            models.Enrollment.objects.filter(
                state=enums.ENROLLMENT_STATE_IN_PROGRESS
            ).count(),
            2,
        )
        # API return details about order just created
        self.assertEqual(content["id"], str(order.uid))
        self.assertEqual(content["owner"], username)
        self.assertEqual(content["product_id"], str(relation1.product.uid))
        self.assertEqual(len(content["enrollments"]), 2)
        self.assertEqual(content["enrollments"][0]["position"], relation1.position)
        self.assertEqual(
            content["enrollments"][0]["resource_link"],
            relation1.course_run.resource_link,
        )
        self.assertEqual(
            content["enrollments"][0]["state"],
            enums.ENROLLMENT_STATE_IN_PROGRESS,
        )
        self.assertEqual(content["enrollments"][1]["position"], relation2.position)
        self.assertEqual(
            content["enrollments"][1]["resource_link"],
            relation2.course_run.resource_link,
        )
        self.assertEqual(
            content["enrollments"][1]["state"],
            enums.ENROLLMENT_STATE_IN_PROGRESS,
        )

        # Now try to enroll again, check error raising
        response = self.client.post(
            "/api/orders/",
            data={
                "id": relation1.product.uid,
                "resource_links": [
                    relation1.course_run.resource_link,
                ],
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)
        # No additional order
        self.assertEqual(models.Order.objects.count(), 1)
        # No additional enrollments
        self.assertEqual(models.Enrollment.objects.count(), 2)
        # It should return an error message
        self.assertEqual(response.data["errors"], ("Order already exists",))

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
                "BASE_URL": "http://openedx.test",
                "SELECTOR_REGEX": r".*openedx.test.*",
                "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            },
        ]
    )
    def test_api_order_post_matched_and_unmatched_course_runs(self):
        """
        If one of resource_link given is not matched by an LMS, we should log an error,
        and create an order but in failure. The matched enrollment should be set.
        """
        # initialize an invalid course run
        unmatched_link = "http://mysterious.uri/courses/course-v0:001+Stuff_run/course"
        relation = factories.ProductCourseRelationFactory(
            course_run__resource_link=unmatched_link
        )
        # Add a valid course run  to the product
        relation_valid = factories.ProductCourseRelationFactory(
            product=relation.product,
            course_run__resource_link=OPENEDX_COURSE_RUN_URI.format("002"),
        )

        # Ask to enroll to the product
        username = "panoramix"
        token = self.get_user_token(username)
        data = {
            "product": relation.product.uid,
        }
        with self.assertLogs(level="ERROR") as logs:
            response = self.client.post(
                "/api/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        msg_error = f"No LMS configuration found for resource link: {unmatched_link}"
        self.assertIn(msg_error, logs.output[0])
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        self.assertEqual(models.User.objects.count(), 1)
        self.assertEqual(models.User.objects.get().username, username)

        # All joanie enrollments were created but with different states
        # and order state was set to 'failed'
        order = models.Order.objects.get()
        self.assertEqual(order.state, enums.ORDER_STATE_FAILED)
        self.assertEqual(models.Enrollment.objects.count(), 2)
        self.assertEqual(
            models.Enrollment.objects.get(
                course_run__resource_link=unmatched_link
            ).state,
            enums.ENROLLMENT_STATE_FAILED,
        )
        self.assertEqual(
            models.Enrollment.objects.filter(
                state=enums.ENROLLMENT_STATE_IN_PROGRESS
            ).count(),
            1,
        )

        self.assertEqual(content["id"], str(order.uid))
        self.assertEqual(content["owner"], username)
        self.assertEqual(content["product_id"], str(relation.product.uid))
        self.assertEqual(content["state"], enums.ORDER_STATE_FAILED)
        self.assertEqual(len(content["enrollments"]), 2)
        self.assertEqual(
            content["enrollments"][0]["resource_link"],
            unmatched_link,
        )
        self.assertEqual(
            content["enrollments"][0]["state"],
            enums.ENROLLMENT_STATE_FAILED,
        )
        self.assertEqual(
            content["enrollments"][0]["position"],
            relation.position,
        )
        self.assertEqual(
            content["enrollments"][1]["resource_link"],
            relation_valid.course_run.resource_link,
        )
        self.assertEqual(
            content["enrollments"][1]["state"],
            enums.ENROLLMENT_STATE_IN_PROGRESS,
        )
        self.assertEqual(
            content["enrollments"][1]["position"],
            relation_valid.position,
        )

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
                "BASE_URL": "http://openedx.test",
                "SELECTOR_REGEX": r".*openedx.test.*",
                "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            },
        ]
    )
    def test_api_order_post_one_unmatched_course_run(self):
        """
        If only one resource_link is given that is not matched by any LMS, we should
        log an error and create an order but in failure.
        """
        # initialize an invalid course run
        unmatched_link = "http://mysterious.uri/courses/course-v0:001+Stuff_run/course"
        relation = factories.ProductCourseRelationFactory(
            course_run__resource_link=unmatched_link
        )

        # Ask to enroll to the product
        username = "panoramix"
        token = self.get_user_token(username)
        data = {
            "product": relation.product.uid,
        }
        with self.assertLogs(level="ERROR") as logs:
            response = self.client.post(
                "/api/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        msg_error = f"No LMS configuration found for resource link: {unmatched_link}"
        self.assertIn(msg_error, logs.output[0])
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        self.assertEqual(models.User.objects.count(), 1)
        self.assertEqual(models.User.objects.get().username, username)

        # All joanie enrollments were created but with different states
        # and order state was set to 'failed'
        order = models.Order.objects.get()
        self.assertEqual(order.state, enums.ORDER_STATE_FAILED)
        self.assertEqual(models.Enrollment.objects.count(), 2)
        self.assertEqual(
            models.Enrollment.objects.get(
                course_run__resource_link=unmatched_link
            ).state,
            enums.ENROLLMENT_STATE_FAILED,
        )
        self.assertEqual(
            models.Enrollment.objects.filter(
                state=enums.ENROLLMENT_STATE_IN_PROGRESS
            ).count(),
            1,
        )

        self.assertEqual(content["id"], str(order.uid))
        self.assertEqual(content["owner"], username)
        self.assertEqual(content["product_id"], str(relation.product.uid))
        self.assertEqual(content["state"], enums.ORDER_STATE_FAILED)
        self.assertEqual(len(content["enrollments"]), 1)
        self.assertEqual(
            content["enrollments"][0]["resource_link"],
            unmatched_link,
        )
        self.assertEqual(
            content["enrollments"][0]["state"],
            enums.ENROLLMENT_STATE_FAILED,
        )
        self.assertEqual(
            content["enrollments"][0]["position"],
            relation.position,
        )

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
                "BASE_URL": "http://openedx.test",
                "SELECTOR_REGEX": r".*openedx.test.*",
                "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            },
        ]
    )
    def test_api_order_post_related_and_unrelated_resource_links(self):
        """
        If set of resource_links given is not related to the product,
        no order or enrollment should be created.
        """
        relation = factories.ProductCourseRelationFactory()
        # Add a valid course run  to the product
        relation_valid = factories.ProductCourseRelationFactory(
            product=relation.product,
            course_run__resource_link=OPENEDX_COURSE_RUN_URI.format("002"),
        )

        # Ask to enroll to the product
        username = "panoramix"
        token = self.get_user_token(username)
        data = {
            "product": relation.product.uid,
        }
        with self.assertLogs(level="ERROR") as logs:
            response = self.client.post(
                "/api/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        msg_error = f"No LMS configuration found for resource link: {unmatched_link}"
        self.assertIn(msg_error, logs.output[0])
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        self.assertEqual(models.User.objects.count(), 1)
        self.assertEqual(models.User.objects.get().username, username)

        # All joanie enrollments were created but with different states
        # and order state was set to 'failed'
        order = models.Order.objects.get()
        self.assertEqual(order.state, enums.ORDER_STATE_FAILED)
        self.assertEqual(models.Enrollment.objects.count(), 2)
        self.assertEqual(
            models.Enrollment.objects.get(
                course_run__resource_link=unmatched_link
            ).state,
            enums.ENROLLMENT_STATE_FAILED,
        )
        self.assertEqual(
            models.Enrollment.objects.filter(
                state=enums.ENROLLMENT_STATE_IN_PROGRESS
            ).count(),
            1,
        )

        self.assertEqual(content["id"], str(order.uid))
        self.assertEqual(content["owner"], username)
        self.assertEqual(content["product_id"], str(relation.product.uid))
        self.assertEqual(content["state"], enums.ORDER_STATE_FAILED)
        self.assertEqual(len(content["enrollments"]), 2)
        self.assertEqual(
            content["enrollments"][0]["resource_link"],
            unmatched_link,
        )
        self.assertEqual(
            content["enrollments"][0]["state"],
            enums.ENROLLMENT_STATE_FAILED,
        )
        self.assertEqual(
            content["enrollments"][0]["position"],
            relation.position,
        )
        self.assertEqual(
            content["enrollments"][1]["resource_link"],
            relation_valid.course_run.resource_link,
        )
        self.assertEqual(
            content["enrollments"][1]["state"],
            enums.ENROLLMENT_STATE_IN_PROGRESS,
        )
        self.assertEqual(
            content["enrollments"][1]["position"],
            relation_valid.position,
        )

    def test_api_orders_get_without_authorization(self):
        """Get user's orders is not possible without HTTP AUTH"""
        # Try to get orders without Authorization
        response = self.client.get(
            "/api/orders/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_orders_get_with_bad_token(self):
        """Get user's orders is not allowed with bad user token"""
        # Try to get orders with bad token
        response = self.client.get(
            "/api/orders/",
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer nawak",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_orders_get_with_expired_token(self):
        """Get user's orders not allowed with an expired token"""
        # Try to get orders with expired token
        token = self.get_user_token(
            "panoramix",
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.get(
            "/api/orders/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
                "BASE_URL": "http://openedx.test",
                "SELECTOR_REGEX": r".*openedx.test.*",
                "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            },
        ]
    )
    def test_api_orders_get(self):
        """Get orders for a user is allowed with valid user token"""
        # initialize all objects to allow to set order
        self._initialize_products_and_courses()

        username = "panoramix"
        token = self.get_user_token(username)
        self.client.post(
            "/api/orders/",
            data=self._get_order_data(),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order = models.Order.objects.get()

        # We want to test GET /api/orders/ return for user
        response = self.client.get(
            "/api/orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        # check pagination
        self.assertEqual(response.data["count"], 1)
        self.assertIsNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
        # check results returned
        self.assertEqual(response.data["results"][0]["id"], str(order.uid))
        self.assertEqual(response.data["results"][0]["owner"], username)
        self.assertEqual(
            response.data["results"][0]["product_id"],
            str(self.become_botanist_product.uid),
        )
        self.assertEqual(
            models.Enrollment.objects.filter(owner__username="panoramix").count(), 3
        )
        self.assertEqual(
            models.Enrollment.objects.filter(
                state=enums.ENROLLMENT_STATE_IN_PROGRESS
            ).count(),
            3,
        )
        order_data = response.data["results"][0]
        self.assertEqual(len(order_data["enrollments"]), 3)
        self.assertEqual(
            order_data["enrollments"][0]["position"],
            1,
        )
        self.assertEqual(
            order_data["enrollments"][0]["resource_link"],
            self.bases_of_botany_run1.resource_link,
        )
        self.assertEqual(
            order_data["enrollments"][0]["state"],
            enums.ENROLLMENT_STATE_IN_PROGRESS,
        )
        self.assertEqual(
            order_data["enrollments"][-1]["position"],
            3,
        )
        self.assertEqual(
            order_data["enrollments"][-1]["resource_link"],
            self.scientific_publication_analysis_run1.resource_link,
        )
        self.assertEqual(
            order_data["enrollments"][-1]["state"],
            enums.ENROLLMENT_STATE_IN_PROGRESS,
        )

        # Test number of request executed
        # first set order for the certified product now to check number of queries executed
        data = {
            "product": self.become_certified_botanist_product.uid,
        }
        self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        factories.OrderFactory.create_batch(10)
        with self.assertNumQueries(
            1  # select user
            + 1  # count order (pagination)
            + 1  # prefetch: 1 request for orders
            + 1  # prefetch: 1 request for enrollments
            + 1  # prefetch: 1 request for course_runs
            + 6  # select product course run position
        ):
            response = self.client.get(
                "/api/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, 200)
