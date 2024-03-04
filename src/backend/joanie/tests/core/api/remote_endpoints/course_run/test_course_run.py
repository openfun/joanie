"""Test suite for remote API endpoints on course run."""

from datetime import timedelta
from http import HTTPStatus

from django.test.utils import override_settings
from django.utils import timezone as django_timezone

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class RemoteEndpointsCourseRunApiTest(BaseAPITestCase):
    """Test suite for remote API endpoints on course run."""

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=[])
    def test_remote_endpoints_course_run_anonymous_without_token(self):
        """
        Anonymous users cannot query our remote endpoint without a token.
        """
        response = self.client.get("/api/v1.0/course-run-metrics/?resource_link=")

        self.assertContains(
            response,
            "You do not have permission to perform this action.",
            status_code=HTTPStatus.FORBIDDEN,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_anonymous_with_invalid_token(self):
        """
        Anonymous users cannot query our remote endpoint with an invalid token.
        """
        response = self.client.get(
            "/api/v1.0/course-run-metrics/?resource_link=",
            HTTP_AUTHORIZATION="Bearer invalid_token",
        )

        self.assertContains(
            response,
            "You do not have permission to perform this action.",
            status_code=HTTPStatus.FORBIDDEN,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_with_valid_token_and_wrong_scheme_prefix_should_fail(
        self,
    ):
        """
        Test the scenario where another server uses the wrong scheme prefix 'Token' instead of
        'Bearer'. It should fail if the token does not precede by the scheme 'Bearer'.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.ARCHIVED_CLOSED,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")

        response = self.client.get(
            f"/api/v1.0/course-run-metrics/?resource_link={resource_link}",
            HTTP_AUTHORIZATION="Token valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            "You do not have permission to perform this action.",
            status_code=HTTPStatus.FORBIDDEN,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_with_valid_token_and_missing_scheme_prefix_should_fail(
        self,
    ):
        """
        Test the scenario where another server sends its requests without the prefix scheme for
        the token. It should fail if the token does not precede by the scheme 'Bearer'.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.ARCHIVED_CLOSED,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")

        response = self.client.get(
            f"/api/v1.0/course-run-metrics/?resource_link={resource_link}",
            HTTP_AUTHORIZATION="valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            "You do not have permission to perform this action.",
            status_code=HTTPStatus.FORBIDDEN,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_anonymous_valid_token_but_with_post_method_should_fail(
        self,
    ):
        """
        Anonymous users cannot query our remote endpoint with a valid token and the post method.
        It should fail and return a 405 status code Method Not Allowed.
        """
        response = self.client.post(
            "/api/v1.0/course-run-metrics/?resource_link=",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            'Method \\"POST\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_anonymous_valid_token_but_with_patch_method_should_fail(
        self,
    ):
        """
        Anonymous users cannot query our remote endpoint with a valid token and the patch method.
        It should fail and return a 405 status code Method Not Allowed.
        """
        response = self.client.patch(
            "/api/v1.0/course-run-metrics/?resource_link=",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            'Method \\"PATCH\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_anonymous_valid_token_but_with_put_method_should_fail(
        self,
    ):
        """
        Anonymous users cannot query our remote endpoint with a valid token and the put method.
        It should fail and return a 405 status code Method Not Allowed.
        """
        response = self.client.put(
            "/api/v1.0/course-run-metrics/?resource_link=",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_anonymous_valid_token_but_with_delete_method_should_fail(
        self,
    ):
        """
        Anonymous users cannot query our remote endpoint with a valid token and the delete method.
        It should fail and return a 405 status code Method Not Allowed.
        """
        response = self.client.delete(
            "/api/v1.0/course-run-metrics/?resource_link=",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_anonymous_valid_token_without_required_query_params(
        self,
    ):
        """
        Anonymous users cannot query our remote endpoint with get method and without the required
        query parameter `resource_link`. It raises a 400 status code.
        """
        response = self.client.get(
            "/api/v1.0/course-run-metrics/",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            "Query parameter `resource_link` is required.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_authenticated_get_method_should_fail(
        self,
    ):
        """
        Authenticated user cannot query our remote endpoint with the get method and a token that
        is not stored in the settings variable `JOANIE_AUTHORIZED_API_TOKENS`.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            "/api/v1.0/course-run-metrics/?resource_link=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "You do not have permission to perform this action.",
            status_code=HTTPStatus.FORBIDDEN,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_authenticated_post_method_should_fail(
        self,
    ):
        """
        Authenticated user cannot query our remote endpoint with the post method and a token that
        is not stored in the settings variable `JOANIE_AUTHORIZED_API_TOKENS`.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.post(
            "/api/v1.0/course-run-metrics/?resource_link=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "You do not have permission to perform this action.",
            status_code=HTTPStatus.FORBIDDEN,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_authenticated_patch_method_should_fail(
        self,
    ):
        """
        Authenticated user cannot query our remote endpoint with the patch method and a token that
        is not stored in the settings variable `JOANIE_AUTHORIZED_API_TOKENS`.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.patch(
            "/api/v1.0/course-run-metrics/?resource_link=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "You do not have permission to perform this action.",
            status_code=HTTPStatus.FORBIDDEN,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_authenticated_delete_method_should_fail(
        self,
    ):
        """
        Authenticated user cannot query our remote endpoint with the delete method and a token that
        is not stored in the settings variable `JOANIE_AUTHORIZED_API_TOKENS`.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.delete(
            "/api/v1.0/course-run-metrics/?resource_link=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "You do not have permission to perform this action.",
            status_code=HTTPStatus.FORBIDDEN,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_with_not_existent_resource_link_as_input_parameter_fails(
        self,
    ):
        """
        When we parse a non existent `resource_link` as input of a course run, it should return an
        error asking to provide an existing `resource_link` as input parameter.
        """
        course = factories.CourseFactory()
        factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.ARCHIVED_OPEN,
            languages="fr",
        )
        resource_link = "http://openedx.test/courses/course-v1:a_fake_one/course"

        response = self.client.get(
            f"/api/v1.0/course-run-metrics/?resource_link={resource_link}",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            "Make sure to give an existing resource link from an ended course run.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_with_ongoing_open_course_run_state_should_fail(
        self,
    ):
        """
        When the course run's end date is not yet reached, for example the state 'ongoing open',
        it should raise the error asking to provide a `resource_link` where the course run
        has reached its end date.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.ONGOING_OPEN,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")

        response = self.client.get(
            f"/api/v1.0/course-run-metrics/?resource_link={resource_link}",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            "Make sure to give an existing resource link from an ended course run.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_with_future_open_course_run_state_should_fail(
        self,
    ):
        """
        When the course run's end date is not yet reached, for example the state 'future open',
        it should raise the error asking to provide a `resource_link` where the course run
        has reached its end date.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.FUTURE_OPEN,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")

        response = self.client.get(
            f"/api/v1.0/course-run-metrics/?resource_link={resource_link}",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            "Make sure to give an existing resource link from an ended course run.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_with_future_not_yet_open_course_run_state_should_fail(
        self,
    ):
        """
        When the course run's end date is not yet reached, for example the state 'future not yet
        open', it should raise the error asking to provide a `resource_link` where the course run
        has reached its end date.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.FUTURE_NOT_YET_OPEN,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")

        response = self.client.get(
            f"/api/v1.0/course-run-metrics/?resource_link={resource_link}",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            "Make sure to give an existing resource link from an ended course run.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_with_future_closed_course_run_state_should_fail(
        self,
    ):
        """
        When the course run's end date is not yet reached, for example the state 'future closed',
        it should raise the error asking to provide a `resource_link` where the course run
        has reached its end date.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.FUTURE_CLOSED,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")

        response = self.client.get(
            f"/api/v1.0/course-run-metrics/?resource_link={resource_link}",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            "Make sure to give an existing resource link from an ended course run.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_with_ongoing_closed_course_run_state_should_fail(
        self,
    ):
        """
        When the course run's end date is not yet reached, for example the state 'ongoing closed',
        it should raise the error asking to provide a `resource_link` where the course run
        has reached its end date.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.ONGOING_CLOSED,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")

        response = self.client.get(
            f"/api/v1.0/course-run-metrics/?resource_link={resource_link}",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            "Make sure to give an existing resource link from an ended course run.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_with_to_be_scheduled_course_run_state_should_fail(
        self,
    ):
        """
        When the course run's end date is not yet reached, for example the state 'to be scheduled',
        it should raise the error asking to provide a `resource_link` where the course run
        has reached its end date.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.TO_BE_SCHEDULED,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")

        response = self.client.get(
            f"/api/v1.0/course-run-metrics/?resource_link={resource_link}",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertContains(
            response,
            "Make sure to give an existing resource link from an ended course run.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_authenticated_with_valid_token_and_the_required_parameter(
        self,
    ):
        """
        Authenticated user can query our remote endpoint if parsing valid token to the headers
        with an existing `resource_link`. The token must be set into the settings variable
        `JOANIE_AUTHORIZED_API_TOKENS`.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        course = factories.CourseFactory(
            organizations=[organization], users=[[user, enums.OWNER]]
        )
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.ARCHIVED_CLOSED,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")

        response = self.client.get(
            f"/api/v1.0/course-run-metrics/?resource_link={resource_link}",
            HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "nb_active_enrollments": 0,
                "nb_validated_certificate_orders": 0,
            },
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_another_server_with_known_token_and_required_query_params(
        self,
    ):
        """
        Test the scenario where another server can query our remote endpoint with the required
        query parameter `resource_link` when it has in its possession a valid token to request.
        No enrollments were made on this course run, so no one bought the access to unlock the
        certifate. We should find in output 0 enrollment and 0 order to access the certificate.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        course = factories.CourseFactory(
            organizations=[organization], users=[[user, enums.OWNER]]
        )
        course_run = factories.CourseRunFactory(
            course=course,
            is_listed=True,
            state=models.CourseState.ARCHIVED_CLOSED,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")
        url = f"/api/v1.0/course-run-metrics/?resource_link={resource_link}"

        response = self.client.get(
            url, HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "nb_active_enrollments": 0,
                "nb_validated_certificate_orders": 0,
            },
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_server_student_not_buy_certificate_at_the_end_of_course(
        self,
    ):
        """
        Test the scenario where a student enrolls to a course run and he does not purchase the
        access to get the certificate. Once the course run's end date is reached,
        the output must indicate 1 enrollment at the end of the course and find 0 certificate that
        was bought.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        course = factories.CourseFactory(
            organizations=[organization], users=[[user, enums.OWNER]]
        )
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.ONGOING_OPEN,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")
        url = f"/api/v1.0/course-run-metrics/?resource_link={resource_link}"
        # Set an enrollment for the course run
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        # Make an order to unlock the access to the certificate
        factories.OrderFactory(
            owner=enrollment.user,
            enrollment=enrollment,
            course=None,
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            product__courses=[enrollment.course_run.course],
        )
        # Close the course run enrollments and set the end date to have "archived" state
        closing_date = django_timezone.now() - timedelta(days=1)
        course_run.enrollment_end = closing_date
        course_run.end = closing_date
        course_run.save()

        response = self.client.get(
            url, HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "nb_active_enrollments": 1,
                "nb_validated_certificate_orders": 0,
            },
        )

    @override_settings(JOANIE_AUTHORIZED_API_TOKENS=["valid_known_secret_token_sample"])
    def test_remote_endpoints_course_run_another_server_valid_token_enrollments_by_resource_link(
        self,
    ):
        """
        Test the scenario where a student enrolls to a course run and purchases the certificate
        before the end of the course run end date.
        Once the course run's end date has been reached, the ouput must indicate 1 enrollment at
        the end of the course run and 1 certificate that was bought.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        course = factories.CourseFactory(
            organizations=[organization], users=[[user, enums.OWNER]]
        )
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.ONGOING_OPEN,
            languages="fr",
        )
        resource_link = f"{course_run.resource_link}".replace("+", "%2B")
        url = f"/api/v1.0/course-run-metrics/?resource_link={resource_link}"
        # Set an enrollment for the course run
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        # Make an order to unlock the access to the certificate
        factories.OrderFactory(
            owner=enrollment.user,
            enrollment=enrollment,
            course=None,
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            product__courses=[enrollment.course_run.course],
            state=enums.ORDER_STATE_VALIDATED,
        )
        # Close the course run enrollments and set the end date to have "archived" state
        closing_date = django_timezone.now() - timedelta(days=1)
        course_run.enrollment_end = closing_date
        course_run.end = closing_date
        course_run.save()

        response = self.client.get(
            url, HTTP_AUTHORIZATION="Bearer valid_known_secret_token_sample"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "nb_active_enrollments": 1,
                "nb_validated_certificate_orders": 1,
            },
        )
