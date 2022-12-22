"""Tests for the Enrollment API."""
# pylint: disable=too-many-lines
import itertools
import json
import random
import uuid
from datetime import timedelta
from logging import Logger
from unittest import mock

from django.test.utils import override_settings
from django.utils import timezone

from joanie.core import enums, exceptions, factories, models
from joanie.core.factories import CourseRunFactory
from joanie.lms_handler.backends.openedx import OpenEdXLMSBackend
from joanie.payment.factories import InvoiceFactory
from joanie.tests.base import BaseAPITestCase


@override_settings(
    JOANIE_LMS_BACKENDS=[
        {
            "API_TOKEN": "FakeEdXAPIKey",
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "BASE_URL": "http://edx:8073",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            "SELECTOR_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
        }
    ]
)
class EnrollmentApiTest(BaseAPITestCase):
    """Test the API of the Enrollment object."""

    def setUp(self):
        super().setUp()
        self.now = timezone.now()

    def create_opened_course_run(self, count=1, **kwargs):
        """Create course runs opened for enrollment."""
        if count > 1:
            return CourseRunFactory.create_batch(
                count,
                start=self.now - timedelta(hours=1),
                end=self.now + timedelta(hours=2),
                enrollment_end=self.now + timedelta(hours=1),
                **kwargs,
            )

        return CourseRunFactory(
            start=self.now - timedelta(hours=1),
            end=self.now + timedelta(hours=2),
            enrollment_end=self.now + timedelta(hours=1),
            **kwargs,
        )

    def create_closed_course_run(self, count=1, **kwargs):
        """Create course runs closed for enrollment."""
        if count > 1:
            return CourseRunFactory.create_batch(
                count,
                start=self.now - timedelta(hours=1),
                end=self.now + timedelta(hours=1),
                enrollment_end=self.now,
                **kwargs,
            )

        return CourseRunFactory(
            start=self.now - timedelta(hours=1),
            end=self.now + timedelta(hours=1),
            enrollment_end=self.now,
            **kwargs,
        )

    def test_api_enrollment_read_list_anonymous(self):
        """It should not be possible to retrieve the list of enrollments for anonymous users."""
        factories.EnrollmentFactory(course_run=self.create_opened_course_run())

        response = self.client.get(
            "/api/v1.0/enrollments/",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)

        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_enrollment_read_list_authenticated(self):
        """Authenticated users retrieving the list of enrollments should only see theirs."""
        enrollment, other_enrollment = factories.EnrollmentFactory.create_batch(
            2, course_run=self.create_opened_course_run()
        )

        # The user can see his/her enrollment
        token = self.get_user_token(enrollment.user.username)

        response = self.client.get(
            "/api/v1.0/enrollments/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        self.assertEqual(
            content,
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(enrollment.id),
                        "course_run": {
                            "id": str(enrollment.course_run.id),
                            "resource_link": enrollment.course_run.resource_link,
                            "title": enrollment.course_run.title,
                            "enrollment_start": enrollment.course_run.enrollment_start.isoformat().replace(  # noqa pylint: disable=line-too-long
                                "+00:00", "Z"
                            ),
                            "enrollment_end": enrollment.course_run.enrollment_end.isoformat().replace(  # noqa pylint: disable=line-too-long
                                "+00:00", "Z"
                            ),
                            "start": enrollment.course_run.start.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "end": enrollment.course_run.end.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "state": {
                                "priority": enrollment.course_run.state["priority"],
                                "text": enrollment.course_run.state["text"],
                                "call_to_action": enrollment.course_run.state[
                                    "call_to_action"
                                ],
                                "datetime": enrollment.course_run.state["datetime"]
                                .isoformat()
                                .replace("+00:00", "Z"),
                            },
                        },
                        "is_active": enrollment.is_active,
                        "state": enrollment.state,
                    }
                ],
            },
        )

        # The user linked to the other enrollment can only see his/her enrollment
        token = self.get_user_token(other_enrollment.user.username)

        response = self.client.get(
            "/api/v1.0/enrollments/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        self.assertEqual(
            content,
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(other_enrollment.id),
                        "course_run": {
                            "id": str(other_enrollment.course_run.id),
                            "resource_link": other_enrollment.course_run.resource_link,
                            "title": other_enrollment.course_run.title,
                            "enrollment_start": other_enrollment.course_run.enrollment_start.isoformat().replace(  # noqa pylint: disable=line-too-long
                                "+00:00", "Z"
                            ),
                            "enrollment_end": other_enrollment.course_run.enrollment_end.isoformat().replace(  # noqa pylint: disable=line-too-long
                                "+00:00", "Z"
                            ),
                            "start": other_enrollment.course_run.start.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "end": other_enrollment.course_run.end.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "state": {
                                "priority": other_enrollment.course_run.state[
                                    "priority"
                                ],
                                "text": other_enrollment.course_run.state["text"],
                                "call_to_action": other_enrollment.course_run.state[
                                    "call_to_action"
                                ],
                                "datetime": other_enrollment.course_run.state[
                                    "datetime"
                                ]
                                .isoformat()
                                .replace("+00:00", "Z"),
                            },
                        },
                        "is_active": other_enrollment.is_active,
                        "state": other_enrollment.state,
                    }
                ],
            },
        )

    def test_api_enrollment_read_list_filtered_by_course_run_id(self):
        """
        Authenticated users retrieving the list of enrollments should be able to filter
        by course run id.
        """
        user = factories.UserFactory()
        [course_run_1, course_run_2] = self.create_opened_course_run(2)

        # User enrolls to both course runs
        enrollment_1 = factories.EnrollmentFactory(user=user, course_run=course_run_1)
        factories.EnrollmentFactory(user=user, course_run=course_run_2)

        token = self.get_user_token(user.username)

        # Retrieve user's enrollment related to the first course_run
        with self.assertNumQueries(7):
            response = self.client.get(
                f"/api/v1.0/enrollments/?course_run={str(course_run_1.id)}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(enrollment_1.id),
                        "course_run": {
                            "id": str(course_run_1.id),
                            "resource_link": course_run_1.resource_link,
                            "title": course_run_1.title,
                            "enrollment_start": course_run_1.enrollment_start.isoformat().replace(  # noqa pylint: disable=line-too-long
                                "+00:00", "Z"
                            ),
                            "enrollment_end": course_run_1.enrollment_end.isoformat().replace(  # noqa pylint: disable=line-too-long
                                "+00:00", "Z"
                            ),
                            "start": course_run_1.start.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "end": course_run_1.end.isoformat().replace("+00:00", "Z"),
                            "state": {
                                "priority": course_run_1.state["priority"],
                                "text": course_run_1.state["text"],
                                "call_to_action": course_run_1.state["call_to_action"],
                                "datetime": course_run_1.state["datetime"]
                                .isoformat()
                                .replace("+00:00", "Z"),
                            },
                        },
                        "is_active": enrollment_1.is_active,
                        "state": enrollment_1.state,
                    }
                ],
            },
        )

    def test_api_enrollment_read_list_filtered_by_invalid_course_run_id(self):
        """
        Authenticated users providing an invalid course run id to filter its enrollments
        should get a 400 error response.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        # Retrieve user's enrollment related to the first course_run
        with self.assertNumQueries(5):
            response = self.client.get(
                "/api/v1.0/enrollments/?course_run=invalid_course_run_id",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"course_run": ["Enter a valid UUID."]})

    def test_api_enrollment_read_detail_anonymous(self):
        """Anonymous users should not be allowed to retrieve an enrollment."""
        enrollment = factories.EnrollmentFactory(
            course_run=self.create_opened_course_run(),
        )

        response = self.client.get(f"/api/v1.0/enrollments/{enrollment.id}/")
        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            {"detail": "Authentication credentials were not provided."},
        )

    def test_api_enrollment_read_detail_authenticated_owner(self):
        """Authenticated users should be allowed to retrieve an enrollment they own."""
        user = factories.UserFactory()
        target_course_runs = self.create_opened_course_run(2)
        product = factories.ProductFactory(
            target_courses=[cr.course for cr in target_course_runs]
        )
        order = factories.OrderFactory(owner=user, product=product)
        # - Create an invoice related to the order to mark it as validated
        InvoiceFactory(order=order, total=order.total)
        enrollment = factories.EnrollmentFactory(
            course_run=target_course_runs[0], user=user
        )
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        self.assertEqual(
            content,
            {
                "id": str(enrollment.id),
                "course_run": {
                    "id": str(enrollment.course_run.id),
                    "resource_link": enrollment.course_run.resource_link,
                    "title": enrollment.course_run.title,
                    "enrollment_start": enrollment.course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": enrollment.course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "start": enrollment.course_run.start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "end": enrollment.course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": enrollment.course_run.state["priority"],
                        "text": enrollment.course_run.state["text"],
                        "call_to_action": enrollment.course_run.state["call_to_action"],
                        "datetime": enrollment.course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z"),
                    },
                },
                "is_active": enrollment.is_active,
                "state": enrollment.state,
            },
        )

    def test_api_enrollment_read_detail_authenticated_not_owner(self):
        """Authenticated users should not be able to retrieve an enrollment they don't own."""
        enrollment = factories.EnrollmentFactory(
            course_run=self.create_opened_course_run()
        )
        token = self.get_user_token("panoramix")

        response = self.client.get(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": "Not found."})

    def test_api_enrollment_create_anonymous(self):
        """Anonymous users should not be able to create an enrollment."""
        course_run = self.create_opened_course_run()
        data = {
            "course_run": course_run.id,
        }
        response = self.client.post(
            "/api/v1.0/enrollments/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_create_authenticated_success(self, mock_set):
        """Any authenticated user should be able to create an enrollment."""
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        is_active = random.choice([True, False])
        mock_set.return_value = is_active

        course_run = self.create_opened_course_run(resource_link=resource_link)
        data = {"course_run": str(course_run.id), "is_active": is_active}
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        content = json.loads(response.content)

        self.assertEqual(models.Enrollment.objects.count(), 1)
        mock_set.assert_called_once_with("panoramix", resource_link, is_active)
        enrollment = models.Enrollment.objects.get()
        self.assertEqual(
            content,
            {
                "id": str(enrollment.id),
                "course_run": {
                    "id": str(course_run.id),
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z"),
                    },
                },
                "is_active": is_active,
                "state": "set",
            },
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    def test_models_enrollment_duplicate_course_run_with_order(self, _mock_set):
        """
        It should not be possible to enroll to course runs of the same course for a
        given order.
        """
        user = factories.UserFactory()
        target_course = factories.CourseFactory()
        course_run1 = self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )
        course_run2 = self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000002+Demo_Course/course",
        )
        product = factories.ProductFactory(target_courses=[target_course])
        order = factories.OrderFactory(owner=user, product=product)
        # - Create an invoice related to the order to mark it as validated
        InvoiceFactory(order=order, total=order.total)

        # Create a pre-existing enrollment and try to enroll to this course's second course run
        factories.EnrollmentFactory(course_run=course_run1, user=user, is_active=True)
        self.assertTrue(models.Enrollment.objects.filter(is_active=True).exists())
        data = {
            "course_run": course_run2.id,
            "is_active": random.choice([True, False]),
        }
        token = self.get_user_token(user.username)

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)

        self.assertEqual(
            content,
            {
                "user": [
                    "You are already enrolled to an opened course run "
                    f'for the course "{course_run2.course.title}".'
                ]
            },
        )

    @mock.patch.object(Logger, "error")
    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_create_authenticated_no_lms(self, mock_set, mock_logger):
        """
        If the resource link does not match any LMS, the enrollment should fail.
        """
        is_active = random.choice([True, False])
        mock_set.return_value = is_active

        course_run = self.create_opened_course_run(resource_link="http://unknown.com/")
        data = {"course_run": course_run.id, "is_active": is_active}
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        content = json.loads(response.content)

        self.assertEqual(models.Enrollment.objects.count(), 1)
        self.assertFalse(mock_set.called)
        enrollment = models.Enrollment.objects.get()
        self.assertEqual(
            content,
            {
                "id": str(enrollment.id),
                "course_run": {
                    "id": str(course_run.id),
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z"),
                    },
                },
                "is_active": is_active,
                "state": "failed",
            },
        )
        mock_logger.assert_called_once_with(
            'No LMS configuration found for course run: "%s".', "http://unknown.com/"
        )

    @mock.patch.object(Logger, "error")
    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_create_authenticated_enrollment_error(
        self, mock_set, mock_logger
    ):
        """
        If the enrollment on the LMS fails, the enrollment object should be marked as failed.
        """

        def enrollment_error(*args, **kwargs):
            raise exceptions.EnrollmentError()

        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        is_active = random.choice([True, False])
        mock_set.side_effect = enrollment_error

        course_run = self.create_opened_course_run(resource_link=resource_link)
        data = {"course_run": course_run.id, "is_active": is_active}
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 201)
        content = json.loads(response.content)

        self.assertEqual(models.Enrollment.objects.count(), 1)
        mock_set.assert_called_once_with("panoramix", resource_link, is_active)
        enrollment = models.Enrollment.objects.get()
        self.assertEqual(
            content,
            {
                "id": str(enrollment.id),
                "course_run": {
                    "id": str(course_run.id),
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z"),
                    },
                },
                "is_active": is_active,
                "state": "failed",
            },
        )
        mock_logger.assert_called_once_with(
            'Enrollment failed for course run "%s".', course_run.resource_link
        )

    def test_api_enrollment_create_authenticated_missing_is_active(self):
        """
        An authenticated user trying to enroll via the API, should get a 400 error
        if the "is_active" field is missing.
        """
        course_run = self.create_opened_course_run()
        data = {"course_run": course_run.id}
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)

        self.assertEqual(
            content,
            {"is_active": ["This field is required."]},
        )
        self.assertFalse(models.Enrollment.objects.exists())

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_create_authenticated_matching_valid_order(self, mock_set):
        """
        While creating an enrollment, a validated order may be specified as long as
        the owner is the logged-in user and the course run matches one of
        the order's target courses.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        is_active = random.choice([True, False])
        mock_set.return_value = is_active

        course_run = self.create_opened_course_run(resource_link=resource_link)
        other_course_run = self.create_opened_course_run()
        product = factories.ProductFactory(
            target_courses=[course_run.course, other_course_run.course]
        )
        order = factories.OrderFactory(product=product)
        # - Create an invoice related to the order to mark it as validated
        InvoiceFactory(order=order, total=order.total)

        data = {"course_run": course_run.id, "order": order.id, "is_active": is_active}
        token = self.get_user_token(order.owner.username)

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        content = json.loads(response.content)

        self.assertEqual(models.Enrollment.objects.count(), 1)
        mock_set.assert_called_once_with(order.owner.username, resource_link, is_active)
        enrollment = models.Enrollment.objects.get()
        self.assertEqual(
            content,
            {
                "id": str(enrollment.id),
                "course_run": {
                    "id": str(course_run.id),
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z"),
                    },
                },
                "is_active": is_active,
                "state": "set",
            },
        )

    def test_api_enrollment_create_authenticated_owner_not_matching(self):
        """
        An authenticated user should not be allowed to create an enrollment linked
        to an order that he/she does not own.
        """
        target_course_runs = self.create_opened_course_run(2, is_listed=False)
        product = factories.ProductFactory(
            target_courses=[cr.course for cr in target_course_runs]
        )
        factories.OrderFactory(product=product)
        course_run = target_course_runs[0]
        data = {
            "course_run": course_run.id,
            "is_active": True,
        }
        token = self.get_user_token("another-username")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)

        self.assertEqual(
            content,
            {
                "__all__": [
                    f'Course run "{course_run.resource_link}" requires a valid order to enroll.'
                ]
            },
        )
        self.assertFalse(models.Enrollment.objects.exists())

    def test_api_enrollment_create_authenticated_matching_unvalidated_order(self):
        """
        It should not be allowed to create an enrollment with an order that is
        not validated for a course linked to a product.
        """
        target_course_runs = self.create_opened_course_run(2, is_listed=False)
        product = factories.ProductFactory(
            target_courses=[cr.course for cr in target_course_runs]
        )
        order = factories.OrderFactory(
            product=product,
            is_canceled=random.choice([True, False]),
        )
        data = {
            "course_run": target_course_runs[0].id,
            "is_active": True,
        }
        token = self.get_user_token(order.owner.username)

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)

        link = target_course_runs[0].resource_link
        self.assertEqual(
            content,
            {"__all__": [f'Course run "{link:s}" requires a valid order to enroll.']},
        )

    def test_api_enrollment_create_authenticated_matching_no_order(self):
        """
        It should not be allowed to create an enrollment without an order for a course
        linked to a product.
        """
        target_course_runs = self.create_opened_course_run(2, is_listed=False)
        factories.ProductFactory(
            target_courses=[cr.course for cr in target_course_runs]
        )
        data = {"course_run": target_course_runs[0].id, "is_active": True}
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)

        link = target_course_runs[0].resource_link
        self.assertEqual(
            content,
            {"__all__": [f'Course run "{link:s}" requires a valid order to enroll.']},
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_create_has_read_only_fields(self, mock_set):
        """
        When user creates an enrollment, it should not be allowed
        to set "id", "state" fields
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        is_active = random.choice([True, False])
        mock_set.return_value = is_active

        course_run = self.create_opened_course_run(resource_link=resource_link)
        data = {
            "course_run": course_run.id,
            "id": uuid.uuid4(),
            "is_active": is_active,
            "state": enums.ENROLLMENT_STATE_FAILED,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/enrollments/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=data,
        )
        self.assertEqual(response.status_code, 201)
        content = json.loads(response.content)

        self.assertEqual(models.Enrollment.objects.count(), 1)
        mock_set.assert_called_once_with("panoramix", resource_link, is_active)
        enrollment = models.Enrollment.objects.get()

        # - Enrollment uid has been generated and state has been set according
        #   to LMSHandler.set_enrollment response
        self.assertNotEqual(enrollment.id, data["id"])
        self.assertEqual(
            content,
            {
                "id": str(enrollment.id),
                "course_run": {
                    "id": str(course_run.id),
                    "resource_link": course_run.resource_link,
                    "title": course_run.title,
                    "enrollment_start": course_run.enrollment_start.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "enrollment_end": course_run.enrollment_end.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "start": course_run.start.isoformat().replace("+00:00", "Z"),
                    "end": course_run.end.isoformat().replace("+00:00", "Z"),
                    "state": {
                        "priority": course_run.state["priority"],
                        "text": course_run.state["text"],
                        "call_to_action": course_run.state["call_to_action"],
                        "datetime": course_run.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z"),
                    },
                },
                "is_active": is_active,
                "state": "set",
            },
        )

    def test_api_enrollment_create_for_closed_course_run(self):
        """An authenticated user should not be allowed to enroll to a closed course run."""
        user = factories.UserFactory()
        token = self.get_user_token(username=user.username)
        target_course = factories.CourseFactory()
        course_run = self.create_closed_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )

        data = {"course_run": course_run.id, "is_active": True}

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json(),
            {
                "__all__": [
                    "You are not allowed to enroll to a course run not opened for enrollment."
                ]
            },
        )

    def test_api_enrollment_create_with_unknown_course_run(self):
        """An authenticated user should not be allowed to enroll to an unknown course run."""

        user = factories.UserFactory()
        token = self.get_user_token(username=user.username)
        course_run = factories.CourseRunFactory.build()
        data = {"course_run": str(course_run.id), "is_active": True}

        response = self.client.post(
            "/api/v1.0/enrollments/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json(),
            {
                "__all__": [
                    ("A course run with id " f'"{course_run.id}" does not exist.')
                ]
            },
        )

    def test_api_enrollment_delete_anonymous(self):
        """Anonymous users should not be able to delete an enrollment."""
        enrollment = factories.EnrollmentFactory(
            course_run=self.create_opened_course_run()
        )

        response = self.client.delete(f"/api/v1.0/enrollments/{enrollment.id}/")

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            {"detail": "Authentication credentials were not provided."},
        )

        self.assertEqual(models.Enrollment.objects.count(), 1)

    def test_api_enrollment_delete_authenticated(self):
        """
        Authenticated users should not be able to delete any enrollment
        whether he/she is staff or even superuser.
        """
        enrollment = factories.EnrollmentFactory(
            course_run=self.create_opened_course_run()
        )
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)

        response = self.client.delete(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Enrollment.objects.count(), 1)

    def test_api_enrollment_delete_owner(self):
        """A user should not be allowed to delete his/her enrollments."""
        enrollment = factories.EnrollmentFactory(
            course_run=self.create_opened_course_run()
        )
        token = self.get_user_token(enrollment.user.username)

        response = self.client.delete(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Enrollment.objects.count(), 1)

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_update_detail_state_anonymous(self, _mock_set):
        """
        Anonymous users should not be allowed to update the state of an
        enrollment.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+{id:05d}+Demo_Course/course"
        )
        # Try setting state starting from any state and going to any state
        for i, (old_state, new_state) in enumerate(
            itertools.product(enums.ENROLLMENT_STATE_CHOICES, repeat=2)
        ):
            enrollment = factories.EnrollmentFactory(
                course_run=self.create_opened_course_run(
                    resource_link=resource_link.format(id=i)
                ),
                state=old_state[0],
            )

            response = self.client.patch(
                f"/api/v1.0/enrollments/{enrollment.id}/",
                data={"state": new_state[0]},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)
            content = json.loads(response.content)

            self.assertEqual(
                content, {"detail": "Authentication credentials were not provided."}
            )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_api_enrollment_update_detail_state_not_owner(self, _mock_set):
        """
        An authenticated user should not be allowed to update the state of an
        enrollment he/she doesn't own, even if he/she is staff or superuser.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.get_user_token(user.username)
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+{id:05d}+Demo_Course/course"
        )

        # Try setting "is_active" starting from any value of the field
        for i, (is_active_old, is_active_new) in enumerate(
            itertools.product([True, False], repeat=2)
        ):
            enrollment = factories.EnrollmentFactory(
                course_run=self.create_opened_course_run(
                    resource_link=resource_link.format(id=i)
                ),
                is_active=is_active_old,
            )

            response = self.client.patch(
                f"/api/v1.0/enrollments/{enrollment.id}/",
                data={"is_active": is_active_new},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, 404)
            content = json.loads(response.content)

            self.assertEqual(content, {"detail": "Not found."})

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    def test_api_enrollment_update_detail_is_active_owner(self, _mock_set):
        """
        The user should be able to update the "is_active" field on his/her enrollments.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+{id:05d}+Demo_Course/course"
        )
        # Try setting "is_active" starting from any value of the field
        for i, (is_active_old, is_active_new) in enumerate(
            itertools.product([True, False], repeat=2)
        ):
            enrollment = factories.EnrollmentFactory(
                course_run=self.create_opened_course_run(
                    resource_link=resource_link.format(id=i)
                ),
                is_active=is_active_old,
            )
            token = self.get_user_token(enrollment.user.username)

            response = self.client.patch(
                f"/api/v1.0/enrollments/{enrollment.id}/",
                data={"is_active": is_active_new},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, 200)
            content = json.loads(response.content)

            self.assertEqual(
                content,
                {
                    "id": str(enrollment.id),
                    "course_run": {
                        "id": str(enrollment.course_run.id),
                        "resource_link": enrollment.course_run.resource_link,
                        "title": enrollment.course_run.title,
                        "enrollment_start": enrollment.course_run.enrollment_start.isoformat().replace(  # noqa pylint: disable=line-too-long
                            "+00:00", "Z"
                        ),
                        "enrollment_end": enrollment.course_run.enrollment_end.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "start": enrollment.course_run.start.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "end": enrollment.course_run.end.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "state": {
                            "priority": enrollment.course_run.state["priority"],
                            "text": enrollment.course_run.state["text"],
                            "call_to_action": enrollment.course_run.state[
                                "call_to_action"
                            ],
                            "datetime": enrollment.course_run.state["datetime"]
                            .isoformat()
                            .replace("+00:00", "Z"),
                        },
                    },
                    "is_active": is_active_new,
                    "state": "set",
                },
            )

    # pylint: disable=too-many-locals
    def _check_api_enrollment_update_detail(self, enrollment, user, http_code):
        """Nobody should be allowed to update an enrollment."""
        user_token = self.get_user_token(enrollment.user.username)

        response = self.client.get(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {user_token}",
        )
        initial_data = json.loads(response.content)

        # Get alternative values to try to modify our enrollment
        other_user = factories.UserFactory(is_superuser=random.choice([True, False]))
        other_order = factories.OrderFactory(
            owner=other_user,
            product=enrollment.course_run.course.targeted_by_products.first(),
        )
        # - Create an invoice related to the order to mark it as validated
        InvoiceFactory(order=other_order, total=other_order.total)

        # Try modifying the enrollment on each field with our alternative data
        course_run = models.CourseRun.objects.exclude(id=enrollment.course_run_id).get()
        new_data = {
            "id": uuid.uuid4(),
            "user": other_user.username,
            "course_run": course_run.id,
            "state": "failed",
        }
        headers = (
            {"HTTP_AUTHORIZATION": f"Bearer {self.get_user_token(user.username)}"}
            if user
            else {}
        )

        response = self.client.patch(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            data=new_data,
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, http_code)

        # Check that nothing was modified
        self.assertEqual(models.Enrollment.objects.count(), 1)
        response = self.client.get(
            f"/api/v1.0/enrollments/{enrollment.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {user_token}",
        )
        new_data = json.loads(response.content)
        self.assertEqual(new_data, initial_data)

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value="enrolled")
    def test_api_enrollment_update_detail_anonymous(self, _mock_set):
        """An anonymous user should not be allowed to update any enrollment."""
        target_course = factories.CourseFactory()
        course_run1 = self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )
        self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000002+Demo_Course/course",
        )
        product = factories.ProductFactory(target_courses=[target_course])
        order = factories.OrderFactory(product=product)
        # - Create an invoice related to the order to mark it as validated
        InvoiceFactory(order=order, total=order.total)
        enrollment = factories.EnrollmentFactory(
            course_run=course_run1, user=order.owner
        )
        self._check_api_enrollment_update_detail(enrollment, None, 401)

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value="enrolled")
    def test_api_enrollment_update_detail_authenticated_superuser(self, _mock_set):
        """A superuser should not be allowed to update any enrollment."""
        user = factories.UserFactory(is_superuser=True, is_staff=True)
        target_course = factories.CourseFactory()
        course_run1 = self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )
        self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000002+Demo_Course/course",
        )
        product = factories.ProductFactory(target_courses=[target_course])
        order = factories.OrderFactory(product=product)
        # - Create an invoice related to the order to mark it as validated
        InvoiceFactory(order=order, total=order.total)
        enrollment = factories.EnrollmentFactory(
            course_run=course_run1, user=order.owner
        )
        self._check_api_enrollment_update_detail(enrollment, user, 404)

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value="enrolled")
    def test_api_enrollment_update_detail_authenticated_owner(self, _mock_set):
        """An authenticated user should not be allowed to update his/her enrollment."""
        user = factories.UserFactory()
        target_course = factories.CourseFactory()
        course_run1 = self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course",
        )
        self.create_opened_course_run(
            course=target_course,
            resource_link="http://openedx.test/courses/course-v1:edx+000002+Demo_Course/course",
        )
        product = factories.ProductFactory(target_courses=[target_course])
        order = factories.OrderFactory(owner=user, product=product)
        # - Create an invoice related to the order to mark it as validated
        InvoiceFactory(order=order, total=order.total)
        enrollment = factories.EnrollmentFactory(course_run=course_run1, user=user)
        self._check_api_enrollment_update_detail(enrollment, user, 200)
