"""
Test suite for API
"""
import json
from datetime import datetime, timedelta

from django.test import TestCase
from django.test.utils import override_settings
from django.utils import translation

import arrow
from rest_framework_simplejwt.tokens import AccessToken

from joanie.core import enums, factories, models

OPENEDX_COURSE_RUN_URI = "http://openedx.test/courses/course-v1:edx+%s/course"


# pylint: disable=too-many-instance-attributes,attribute-defined-outside-init
class APITestCase(TestCase):
    """Test suite for API"""

    def setUp(self):
        """
        Create a credible context to test API. Initialize some courses, course runs and products.
        """
        super().setUp()
        translation.activate("en-us")

    def _initialize_products_and_courses(self):
        # First create a course product to learn how to become a botanist
        # 1/ some course runs are required to became a botanist
        self.bases_of_botany_run1 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI % "000001+BasesOfBotany_run1",
            start=arrow.utcnow().shift(days=-2).datetime,
        )
        self.bases_of_botany_run2 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI % "000001+BasesOfBotany_run2",
            start=arrow.utcnow().shift(days=10).datetime,
        )
        self.how_to_make_a_herbarium_run1 = factories.CourseRunFactory(
            title="How to make a herbarium",
            resource_link=OPENEDX_COURSE_RUN_URI % "000002+HowToMakeHerbarium_run1",
        )
        self.how_to_make_a_herbarium_run2 = factories.CourseRunFactory(
            title="How to make a herbarium",
            resource_link=OPENEDX_COURSE_RUN_URI % "000002+HowToMakeHerbarium_run2",
        )
        self.scientific_publication_analysis_run1 = factories.CourseRunFactory(
            title="Scientific publication analysis",
            resource_link=OPENEDX_COURSE_RUN_URI
            % "000003+ScientificPublicationAnalysis_run1",
        )
        self.scientific_publication_analysis_run2 = factories.CourseRunFactory(
            title="Scientific publication analysis",
            resource_link=OPENEDX_COURSE_RUN_URI
            % "000003+ScientificPublicationAnalysis_run2",
        )
        botanist_course_runs = [
            self.bases_of_botany_run1,
            self.bases_of_botany_run2,
            self.how_to_make_a_herbarium_run1,
            self.how_to_make_a_herbarium_run2,
            self.scientific_publication_analysis_run1,
            self.scientific_publication_analysis_run2,
        ]
        botanist_course_runs_position_todo = [
            (1, self.bases_of_botany_run1),
            (1, self.bases_of_botany_run2),
            (2, self.how_to_make_a_herbarium_run1),
            (2, self.how_to_make_a_herbarium_run2),
            (3, self.scientific_publication_analysis_run1),
            (3, self.scientific_publication_analysis_run2),
        ]

        # 2/ Create the Course of organization "the Botany School"
        self.botanist_course = factories.CourseFactory(
            title="botany course",
            organization=factories.OrganizationFactory(title="the Botany School"),
        )
        # 3/ Create the enrollment product for the botany course
        self.become_botanist_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_ENROLLMENT,
            title="Become botanist",
            course=self.botanist_course,
            price=100,
        )
        # 4/ add all course runs available for this course product
        self.become_botanist_product.course_runs.set(botanist_course_runs)

        # 5/ now define position of each course runs to complete the course
        for position, course_run in botanist_course_runs_position_todo:
            factories.ProductCourseRunPositionFactory(
                product=self.become_botanist_product,
                position=position,
                course_run=course_run,
            )

        # Now create a course product to learn how to become a botanist and get a certificate
        # 1/ Create the credential Product linked to the botany Course
        self.become_certified_botanist_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            title="Become a certified botanist",
            course=self.botanist_course,
            certificate_definition=factories.CertificateDefinitionFactory(
                title="Botanist Certification",
            ),
        )
        # 2/ add all course runs available for this course product
        self.become_certified_botanist_product.course_runs.set(botanist_course_runs)

        # 3/ now define position of each course runs to complete the course
        for position, course_run in botanist_course_runs_position_todo:
            factories.ProductCourseRunPositionFactory(
                product=self.become_certified_botanist_product,
                position=position,
                course_run=course_run,
            )

    def _get_order_data(self):
        """
        Return valid data to set an order.
        It's a selection of course runs for an existing course product
        """
        # we choose to take the 3 default course runs for the botany course (run1)
        # so we give the product uid and all resource_links of course runs selected
        return {
            "id": self.become_botanist_product.uid,
            "resource_links": [
                self.bases_of_botany_run1.resource_link,
                self.how_to_make_a_herbarium_run1.resource_link,
                self.scientific_publication_analysis_run1.resource_link,
            ],
        }

    @staticmethod
    def _mock_user_token(username, expires_at=None):
        """
        Mock the jwt token used to authenticate a user

        Args:
            username: str, username to encode
            expires_at: datetime.datetime, time after which the token should expire.

        Returns:
            token, the jwt token generated as it should
        """
        issued_at = datetime.utcnow()
        token = AccessToken()
        token.payload.update(
            {
                "email": f"{username}@funmooc.fr",
                "username": username,
                "exp": expires_at or issued_at + timedelta(days=2),
                "iat": issued_at,
            }
        )
        return token

    def test_get_products_available_for_a_course(self):
        """
        Just check that we can get all products available for a course.
        No authentication or permission is needed.
        """
        # initialize all objects to allow to get course products
        self._initialize_products_and_courses()

        # Get all products available for botany course
        with self.assertNumQueries(
            1  # select course
            + 1  # select product
            + 2  # select course run positions x 2 products
        ):
            response = self.client.get(
                f"/api/courses/{self.botanist_course.code}/products"
            )
        self.assertEqual(response.status_code, 200)
        # two products are available: become_botanist_product and become_certified_botanist_product
        self.assertEqual(response.data[1]["id"], str(self.become_botanist_product.uid))
        self.assertEqual(
            response.data[1]["title"],
            self.become_botanist_product.title,
        )
        self.assertEqual(
            response.data[1]["call_to_action"],
            self.become_botanist_product.call_to_action,
            "let's go!",
        )
        self.assertEqual(
            int(response.data[1]["price"]),
            self.become_botanist_product.price,
            100,
        )
        # 2 sessions are available for each course run (2x3)
        self.assertEqual(len(response.data[1]["course_runs"]), 6)

        # check ordering by position then start date
        self.assertEqual(response.data[1]["course_runs"][0]["position"], 1)
        self.assertEqual(response.data[1]["course_runs"][-1]["position"], 3)
        # check course run details returned
        self.assertEqual(
            response.data[1]["course_runs"][0]["title"],
            self.bases_of_botany_run1.title,
        )
        self.assertEqual(
            response.data[1]["course_runs"][0]["resource_link"],
            self.bases_of_botany_run1.resource_link,
        )
        self.assertEqual(
            response.data[0]["id"], str(self.become_certified_botanist_product.uid)
        )
        self.assertEqual(
            response.data[0]["title"],
            self.become_certified_botanist_product.title,
        )
        # 2 sessions are available for each course run (2x3)
        self.assertEqual(len(response.data[0]["course_runs"]), 6)

    def test_set_order_without_authorization(self):
        """Order creation not allowed without HTTP AUTH"""
        # initialize all objects to allow to set order
        self._initialize_products_and_courses()

        # Try to set order without Authorization
        response = self.client.post(
            "/api/orders/",
            data=self._get_order_data(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_set_order_with_bad_token(self):
        """Order creation not allowed with bad user token"""
        # initialize all objects to allow to set order
        self._initialize_products_and_courses()

        # Try to set order with bad token
        response = self.client.post(
            "/api/orders/",
            data=self._get_order_data(),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer nawak",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_set_order_with_expired_token(self):
        """Order creation not allowed with user token expired"""
        # initialize all objects to allow to set order
        self._initialize_products_and_courses()

        # Try to set order with expired token
        token = self._mock_user_token(
            "panoramix",
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.post(
            "/api/orders/",
            data=self._get_order_data(),
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
    def test_set_order_lms_fail(self):
        """
        Test order creation with broken lms
        """
        # initialize all objects to allow to set order
        self._initialize_products_and_courses()

        # Set an order for the botany course to a new user Panoramix
        self.assertEqual(models.User.objects.count(), 0)

        username = "panoramix"

        # we call api with a valid token
        token = self._mock_user_token(username)
        with self.assertLogs(level="ERROR") as logs:
            response = self.client.post(
                "/api/orders/",
                data=self._get_order_data(),
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
        self.assertEqual(order.enrollments.count(), 3)
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
    def test_set_order(self):
        """
        Order creation is allowed with a valid user token given
        and valid data about the product and its course runs selected
        """
        # initialize all objects to allow to set order
        self._initialize_products_and_courses()

        # Set an order for the botany course to a new user Panoramix
        self.assertEqual(models.User.objects.count(), 0)

        username = "panoramix"

        # we call api with a valid token
        token = self._mock_user_token(username)
        response = self.client.post(
            "/api/orders/",
            data=self._get_order_data(),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        # panoramix was a unknown user, so a new user was created
        self.assertEqual(models.User.objects.get().username, username)

        # an order was created at pending state
        order = models.Order.objects.get()
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)
        # the 3 course runs selected was linked to the order
        self.assertEqual(order.course_runs.count(), 3)
        # 3 enrollments was created for each course run at 'in progress' state
        self.assertEqual(models.Enrollment.objects.count(), 3)
        self.assertEqual(
            models.Enrollment.objects.filter(
                state=enums.ENROLLMENT_STATE_IN_PROGRESS
            ).count(),
            3,
        )
        # api return details about order just created
        order_data = response.data
        self.assertEqual(order_data["id"], str(order.uid))
        self.assertEqual(order_data["owner"], username)
        self.assertEqual(
            order_data["product_id"], str(self.become_botanist_product.uid)
        )
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

        # Now try to enroll again, check error raising
        response = self.client.post(
            "/api/orders/",
            data=self._get_order_data(),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)
        # no more order
        self.assertEqual(models.Order.objects.count(), 1)
        # no more enrollments
        self.assertEqual(models.Enrollment.objects.count(), 3)
        # return an error message
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
    def test_set_order_to_one_invalid_course_run(self):
        """
        If one of resource_link given is not valid, log error, order was created but in failure,
        other enrollments were done.
        """
        # initialize all objects to allow to set order
        self._initialize_products_and_courses()

        # initialize an invalid course run
        resource_link_invalid = (
            "http://mysterious.uri/courses/course-v0:001+Stuff_run/course"
        )
        invalid_course_run = factories.CourseRunFactory(
            title="How to do some stuff?",
            resource_link=resource_link_invalid,
        )
        # add invalid course run to the desired product
        self.become_botanist_product.course_runs.add(invalid_course_run)
        factories.ProductCourseRunPositionFactory(
            course_run=invalid_course_run,
            position=4,
            product=self.become_botanist_product,
        )

        # ask to enroll to the product
        username = "panoramix"
        token = self._mock_user_token(username)
        data = {
            "id": self.become_botanist_product.uid,
            "resource_links": [
                invalid_course_run.resource_link,
                self.bases_of_botany_run1.resource_link,
                self.how_to_make_a_herbarium_run1.resource_link,
                self.scientific_publication_analysis_run1.resource_link,
            ],
        }
        with self.assertLogs(level="ERROR") as logs:
            response = self.client.post(
                "/api/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            msg_error = (
                f"No LMS configuration found for resource link: {resource_link_invalid}"
            )
            self.assertIn(msg_error, logs.output[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(models.User.objects.count(), 1)
        self.assertEqual(models.User.objects.get().username, username)

        # all joanie enrollments were created but with different states
        # and order state was set to 'failed'
        order = models.Order.objects.get()
        self.assertEqual(order.state, enums.ORDER_STATE_FAILED)
        self.assertEqual(models.Enrollment.objects.count(), 4)
        self.assertEqual(
            models.Enrollment.objects.get(
                course_run__resource_link=resource_link_invalid
            ).state,
            enums.ENROLLMENT_STATE_FAILED,
        )
        self.assertEqual(
            models.Enrollment.objects.filter(
                state=enums.ENROLLMENT_STATE_IN_PROGRESS
            ).count(),
            3,
        )
        order_data = response.data
        self.assertEqual(order_data["id"], str(order.uid))
        self.assertEqual(order_data["owner"], username)
        self.assertEqual(
            order_data["product_id"], str(self.become_botanist_product.uid)
        )
        self.assertEqual(order_data["state"], enums.ORDER_STATE_FAILED)
        self.assertEqual(len(order_data["enrollments"]), 4)
        self.assertEqual(
            order_data["enrollments"][3]["resource_link"],
            resource_link_invalid,
        )
        self.assertEqual(
            order_data["enrollments"][3]["state"],
            enums.ENROLLMENT_STATE_FAILED,
        )
        self.assertEqual(
            order_data["enrollments"][3]["position"],
            4,
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
            order_data["enrollments"][0]["position"],
            1,
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
    def test_set_order_with_crazy_set_of_course_runs(self):
        """
        If set of resource_links given is not valid, log error, no order and enrollment created.
        """
        # initialize all objects to allow to set order
        self._initialize_products_and_courses()

        # ask to enroll to the product
        username = "panoramix"
        token = self._mock_user_token(username)
        data = {
            "id": self.become_botanist_product.uid,
            "resource_links": [
                self.bases_of_botany_run1.resource_link,
                self.bases_of_botany_run1.resource_link,
                self.bases_of_botany_run1.resource_link,
            ],
        }
        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(
            content,
            {
                "errors": [
                    "3 course runs have to be selected, 1 given",
                ]
            },
        )
        self.assertEqual(models.User.objects.count(), 1)
        self.assertEqual(models.User.objects.get().username, username)

        self.assertEqual(models.Order.objects.count(), 0)
        self.assertEqual(models.Enrollment.objects.count(), 0)

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
    def test_set_order_with_invalid_set_of_course_runs(self):
        """
        If set of resource_links given is not valid, no order and enrollment created.
        """
        # initialize all objects to allow to set order
        self._initialize_products_and_courses()

        # ask to enroll to the product
        username = "panoramix"
        token = self._mock_user_token(username)
        # we try to enroll to two course runs on the same position
        data = {
            "id": self.become_botanist_product.uid,
            "resource_links": [
                self.bases_of_botany_run1.resource_link,
                self.bases_of_botany_run2.resource_link,
                self.how_to_make_a_herbarium_run1.resource_link,
            ],
        }
        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(models.User.objects.count(), 1)
        self.assertEqual(models.User.objects.get().username, username)

        self.assertEqual(models.Order.objects.count(), 0)
        self.assertEqual(models.Enrollment.objects.count(), 0)

        # Try with the minimal course runs set with two same sessions
        data = {
            "id": self.become_botanist_product.uid,
            "resource_links": [
                self.bases_of_botany_run1.resource_link,
                self.bases_of_botany_run2.resource_link,
                self.how_to_make_a_herbarium_run1.resource_link,
                self.scientific_publication_analysis_run1.resource_link,
            ],
        }
        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)

        self.assertEqual(models.Order.objects.count(), 0)
        self.assertEqual(models.Enrollment.objects.count(), 0)

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
    def test_set_order_with_course_run_unavailable_for_product_selected(self):
        """
        If set of resource_links given is not valid, log error, no order and enrollment created.
        """
        # initialize all objects to allow to set order
        self._initialize_products_and_courses()

        # create a course run not available for productb become botanist
        other_course_run = factories.CourseRunFactory(
            resource_link=OPENEDX_COURSE_RUN_URI % "000001+HowToDoSomeStuff",
        )

        # ask to enroll to the product
        username = "panoramix"
        token = self._mock_user_token(username)
        data = {
            "id": self.become_botanist_product.uid,
            "resource_links": [
                self.bases_of_botany_run1.resource_link,
                self.how_to_make_a_herbarium_run1.resource_link,
                other_course_run.resource_link,
            ],
        }
        response = self.client.post(
            "/api/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(models.User.objects.count(), 1)
        self.assertEqual(models.User.objects.get().username, username)

        self.assertEqual(models.Order.objects.count(), 0)
        self.assertEqual(models.Enrollment.objects.count(), 0)

    def test_get_orders_without_authorization(self):
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

    def test_get_orders_with_bad_token(self):
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

    def test_get_orders_with_expired_token(self):
        """Get user's orders not allowed with an expired token"""
        # Try to get orders with expired token
        token = self._mock_user_token(
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
    def test_get_orders(self):
        """Get orders for a user is allowed with valid user token"""
        # initialize all objects to allow to set order
        self._initialize_products_and_courses()

        username = "panoramix"
        token = self._mock_user_token(username)
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
        self.assertEqual(models.Enrollment.objects.count(), 3)
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
            "id": self.become_certified_botanist_product.uid,
            "resource_links": [
                self.bases_of_botany_run2.resource_link,
                self.how_to_make_a_herbarium_run2.resource_link,
                self.scientific_publication_analysis_run2.resource_link,
            ],
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
