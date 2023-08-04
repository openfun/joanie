"""Test suite for the OpenEdX LMS Backend."""
import json
import random
from datetime import timedelta

from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

import responses

from joanie.core import factories, models
from joanie.core.exceptions import EnrollmentError, GradeError
from joanie.lms_handler import LMSHandler
from joanie.lms_handler.backends.openedx import OpenEdXLMSBackend


@override_settings(
    JOANIE_LMS_BACKENDS=[
        {
            "API_TOKEN": "a_secure_api_token",
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "BASE_URL": "http://openedx.test",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            "SELECTOR_REGEX": r".*",
        }
    ]
)
class OpenEdXLMSBackendTestCase(TestCase):
    """Test suite for the OpenEdX LMS Backend."""

    def setUp(self):
        super().setUp()
        self.now = timezone.now()

    def test_backend_openedx_extract_course_id_from_resource_link(self):
        """
        From a resource_link, OpenEdX backend should be able
        to extract a course_id
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        course_id = backend.extract_course_id(resource_link)
        self.assertEqual(course_id, "course-v1:edx+000001+Demo_Course")

    @responses.activate
    def test_backend_openedx_get_enrollment_to_a_course_which_user_is_enrolled(self):
        """
        Retrieving course run's enrollment which the provided user is enrolled
        should return enrollment details.
        """
        username = "joanie"
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        url = (
            "http://openedx.test/api/enrollment/v1/enrollment/"
            f"{username},course-v1:edx+000001+Demo_Course"
        )
        expected_json_response = {"is_active": True}

        responses.add(
            responses.GET,
            url,
            status=200,
            json=expected_json_response,
        )

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        enrollment = backend.get_enrollment(username, resource_link)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        self.assertIsNone(responses.calls[0].request.body)
        self.assertEqual(enrollment, expected_json_response)

    @responses.activate
    def test_backend_openedx_get_enrollment_failed(self):
        """
        If retrieving course run's enrollment failed, it should return None.
        """
        username = "joanie"
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        url = (
            "http://openedx.test/api/enrollment/v1/enrollment/"
            f"{username},course-v1:edx+000001+Demo_Course"
        )

        responses.add(
            responses.GET, url, status=500, json={"error": "Something went wrong..."}
        )

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        enrollment = backend.get_enrollment(username, resource_link)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        self.assertIsNone(responses.calls[0].request.body)
        self.assertIsNone(enrollment)

    @responses.activate
    def test_backend_openedx_set_enrollment_successfully(self):
        """
        Updating a user's enrollment to a course run should return a boolean
        corresponding to the success of the operation.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        course_run = factories.CourseRunFactory(
            start=self.now - timedelta(hours=1),
            end=self.now + timedelta(hours=2),
            enrollment_end=self.now + timedelta(hours=1),
            is_listed=True,
            resource_link=resource_link,
        )
        resource_link = course_run.resource_link
        user = factories.UserFactory()
        is_active = random.choice([True, False])
        enrollment = models.Enrollment(
            course_run=course_run, user=user, is_active=is_active
        )
        url = "http://openedx.test/api/enrollment/v1/enrollment"

        responses.add(
            responses.POST,
            url,
            status=200,
            json={"is_active": is_active},
        )

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        result = backend.set_enrollment(enrollment)

        self.assertIsNone(result)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )

        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": is_active,
                "mode": "honor",
                "user": user.username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

    @responses.activate
    def test_backend_openedx_set_enrollment_with_preexisting_enrollment(self):
        """
        Enrolling to OpenEdX via an order should set preexisting enrollment to the "verified" mode.
        """
        url = "http://openedx.test/api/enrollment/v1/enrollment"
        responses.add(
            responses.POST,
            url,
            status=200,
            json={"is_active": True},
        )

        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        course_run = factories.CourseRunFactory(
            is_listed=True,
            resource_link=resource_link,
            state=models.CourseState.ONGOING_OPEN,
        )
        product = factories.ProductFactory(
            target_courses=[course_run.course],
            price="0.00",
        )
        user = factories.UserFactory()
        factories.EnrollmentFactory(
            course_run=course_run,
            user=user,
            # Whether the enrollment comes from an order or not
            was_created_by_order=random.choice([True, False]),
        )
        order = factories.OrderFactory(product=product, owner=user)
        self.assertEqual(len(responses.calls), 0)

        order.submit()

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": True,
                "mode": "verified",
                "user": user.username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

    @responses.activate
    def test_backend_openedx_set_enrollment_with_related_certificate_product(self):
        """
        Buying a certificate for a course run to which the user is enrolled should set the
        enrollment to the "verified" mode.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        course_run = factories.CourseRunFactory(
            is_listed=True,
            resource_link=resource_link,
            state=models.CourseState.ONGOING_OPEN,
        )
        user = factories.UserFactory()
        is_active = random.choice([True, False])
        url = "http://openedx.test/api/enrollment/v1/enrollment"

        responses.add(
            responses.POST,
            url,
            status=200,
            json={"is_active": is_active},
        )

        enrollment = factories.EnrollmentFactory(
            course_run=course_run,
            user=user,
            is_active=is_active,
        )
        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        result = backend.set_enrollment(enrollment)

        self.assertIsNone(result)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": is_active,
                "mode": "honor",
                "user": user.username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

        order = factories.OrderFactory(
            course=None,
            enrollment=enrollment,
            product__type="certificate",
            state="validated",
        )
        result = backend.set_enrollment(enrollment)

        self.assertIsNone(result)
        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(
            json.loads(responses.calls[1].request.body),
            {
                "is_active": is_active,
                "mode": "verified",
                "user": user.username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

        # If the order is later canceled, the enrollment should be set back to honor
        order.cancel()

        self.assertEqual(len(responses.calls), 3)
        self.assertEqual(
            json.loads(responses.calls[2].request.body),
            {
                "is_active": is_active,
                "mode": "honor",
                "user": user.username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

    @responses.activate
    def test_backend_openedx_set_enrollment_wrong_state(self):
        """
        When updating a user's enrollment, the LMS may return a 200 but not
        with the enrollment status we requested. We should not fall for this.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )
        course_run = factories.CourseRunFactory(
            start=self.now - timedelta(hours=1),
            end=self.now + timedelta(hours=2),
            enrollment_end=self.now + timedelta(hours=1),
            is_listed=True,
            resource_link=resource_link,
        )
        resource_link = course_run.resource_link
        user = factories.UserFactory()
        is_active = random.choice([True, False])
        enrollment = models.Enrollment(
            course_run=course_run, user=user, is_active=is_active
        )
        url = "http://openedx.test/api/enrollment/v1/enrollment"

        # Let the LMS return the wrong activation status
        lms_is_active = not is_active
        expected_json_response = {"is_active": lms_is_active}

        responses.add(
            responses.POST,
            url,
            status=200,
            json=expected_json_response,
        )

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        with self.assertRaises(EnrollmentError):
            backend.set_enrollment(enrollment)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )

        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": is_active,
                "mode": "honor",
                "user": user.username,
                "course_details": {"course_id": "course-v1:edx+000001+Demo_Course"},
            },
        )

    @responses.activate
    def test_backend_openedx_set_enrollment_failed(self):
        """
        In case updating a user's enrollment to a course run failed,
        it should raise an EnrollmentError.
        """
        course_run = factories.CourseRunFactory(
            start=self.now - timedelta(hours=1),
            end=self.now + timedelta(hours=2),
            enrollment_end=self.now + timedelta(hours=1),
            is_listed=True,
        )
        resource_link = course_run.resource_link
        user = factories.UserFactory()
        is_active = random.choice([True, False])
        enrollment = models.Enrollment(
            course_run=course_run, user=user, is_active=is_active
        )
        url = "http://openedx.test/api/enrollment/v1/enrollment"

        responses.add(
            responses.POST,
            url,
            status=500,
            json={"is_active": is_active},
        )

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        course_id = backend.extract_course_id(resource_link)

        with self.assertRaises(EnrollmentError):
            backend.set_enrollment(enrollment)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )

        self.assertEqual(
            json.loads(responses.calls[0].request.body),
            {
                "is_active": is_active,
                "mode": "honor",
                "user": user.username,
                "course_details": {"course_id": course_id},
            },
        )

    @responses.activate
    def test_backend_openedx_get_grades_successfully(self):
        """
        When get user's grades for a course run, it should return grade details without
        any data transformation
        """
        username = "joanie"
        course_id = "course-v1:edx+000001+Demo_Course"
        resource_link = f"http://openedx.test/courses/{course_id}/course"
        url = f"http://openedx.test/fun/api/grades/{course_id}/{username}"
        grade_state = random.choice([True, False])
        expected_response = {
            "passed": grade_state,
            "grade": "Pass" if grade_state else "Fail",
            "percent": 1.0 if grade_state else 0.0,
        }

        responses.add(responses.GET, url, status=200, json=expected_response)

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        grade_summary = backend.get_grades(username, resource_link)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )

        self.assertEqual(grade_summary, expected_response)

    @responses.activate
    def test_backend_openedx_get_grades_failed(self):
        """
        When get user's grades for a course run failed,
        it should raise a GradeError
        """
        username = "joanie"
        course_id = "course-v1:edx+000001+Demo_Course"
        resource_link = f"http://openedx.test/courses/{course_id}/course"
        url = f"http://openedx.test/fun/api/grades/{course_id}/{username}"

        responses.add(responses.GET, url, status=500)

        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, OpenEdXLMSBackend)

        with self.assertRaises(GradeError):
            backend.get_grades(username, resource_link)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, url)
        self.assertEqual(
            responses.calls[0].request.headers["X-Edx-Api-Key"], "a_secure_api_token"
        )
