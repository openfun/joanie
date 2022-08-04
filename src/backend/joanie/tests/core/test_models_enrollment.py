"""
Test suite for order models
"""
from datetime import timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from joanie.core import factories
from joanie.core.exceptions import GradeError
from joanie.lms_handler.backends.openedx import OpenEdXLMSBackend


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
class EnrollmentModelsTestCase(TestCase):
    """Test suite for the Enrollment model."""

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    def test_models_enrollment_str_active(self, _mock_set):
        """The string representation should work as expected for an active enrollment."""
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )

        course_run = factories.CourseRunFactory(
            title="my run",
            resource_link=resource_link,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )

        enrollment = factories.EnrollmentFactory(
            course_run=course_run,
            user__username="Françoise",
            is_active=True,
        )

        self.assertEqual(
            str(enrollment),
            (
                "[active][set] Françoise for my run "
                f"[{course_run.start:%Y-%m-%d} to {course_run.end:%Y-%m-%d}]"
            ),
        )

    def test_models_enrollment_str_inactive(self):
        """The string representation should work as expected for an inactive enrollment."""

        course_run = factories.CourseRunFactory(
            title="my run",
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )

        enrollment = factories.EnrollmentFactory(
            course_run=course_run,
            user__username="Françoise",
            is_active=False,
        )

        self.assertEqual(
            str(enrollment),
            (
                "[inactive][failed] Françoise for my run "
                f"[{course_run.start:%Y-%m-%d} to {course_run.end:%Y-%m-%d}]"
            ),
        )

    def test_models_enrollment_unique_course_run_user(self):
        """
        A user can only have one enrollment on a given course run.
        """
        course_run = factories.CourseRunFactory(
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )

        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=False)
        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(
                course_run=enrollment.course_run, user=enrollment.user
            )
        self.assertEqual(
            "{'__all__': ['Enrollment with this Course run and User already exists.']}",
            str(context.exception),
        )

    def test_models_enrollment_unique_opened_course_run_per_course_and_user(self):
        """
        A user can only have one enrollment for an opened course run for a course.
        """
        [cr1, cr2] = factories.CourseRunFactory.create_batch(
            2,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            course=factories.CourseFactory(),
        )

        enrollment = factories.EnrollmentFactory(course_run=cr1, is_active=True)
        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(course_run=cr2, user=enrollment.user)

        self.assertEqual(
            (
                "{'user': ['You are already enrolled to an opened course run "
                f'for the course "{cr2.course.title}".\']}}'
            ),
            str(context.exception),
        )

    def test_models_enrollment_forbid_for_non_listed_course_run(self):
        """If a course run is not listed, user should not be allowed to enroll."""
        course_run = factories.CourseRunFactory(
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            is_listed=False,
        )

        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(course_run=course_run)

        self.assertEqual(
            "{'__all__': ['You are not allowed to enroll to a course run not listed.']}",
            str(context.exception),
        )

    def test_models_enrollment_allows_for_non_listed_course_run_with_product(self):
        """
        If a course run is not listed but linked to a product,
        user should be allowed to enroll if he/she purchased the product.
        """
        user = factories.UserFactory()
        course_run = factories.CourseRunFactory.create_batch(
            2,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            is_listed=False,
            course=factories.CourseFactory(),
        )[0]
        product = factories.ProductFactory(
            target_courses=[course_run.course], price="0.00"
        )

        # - Enrollment should be forbid as user does not purchase the product
        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(course_run=course_run, user=user)

        self.assertEqual(
            (
                f"{{'__all__': ['Course run \"{course_run.resource_link:s}\" "
                "requires a valid order to enroll.']}"
            ),
            str(context.exception),
        )

        # - Once the product purchased, enrollment should be allowed
        factories.OrderFactory(owner=user, product=product)
        factories.EnrollmentFactory(course_run=course_run, user=user)

    def test_models_enrollment_forbid_for_non_listed_course_run_not_included_in_product(
        self,
    ):
        """
        If a course run is not listed and not linked to a product,
        user should not be allowed to enroll to this course run
        even if he/she purchased the product.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        [cr1, cr2] = factories.CourseRunFactory.create_batch(
            2,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            is_listed=False,
            course=course,
        )
        product = factories.ProductFactory(target_courses=[course], price="0.00")

        # - Restrict available course runs for this product to cr1
        course_relation = product.course_relations.get(course=course)
        course_relation.course_runs.set([cr1])

        factories.OrderFactory(owner=user, product=product)

        # - Enroll to cr2 should fail
        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(course_run=cr2, user=user)

        self.assertEqual(
            (
                f"{{'__all__': ['Course run \"{cr2.resource_link}\" "
                "requires a valid order to enroll.']}"
            ),
            str(context.exception),
        )
        self.assertEqual(user.enrollments.count(), 0)

        # - But user should be allowed to enroll to cr1
        factories.EnrollmentFactory(course_run=cr1, user=user)
        self.assertEqual(user.enrollments.count(), 1)

    @override_settings(JOANIE_ENROLLMENT_GRADE_CACHE_TTL=600)
    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    @mock.patch.object(OpenEdXLMSBackend, "get_grades", return_value={"passed": True})
    def test_models_enrollment_is_passed(self, mock_get_grades, _):
        """
        The `is_passed` property should use the get_grades method of the LMS to retrieve
        information then store in cache the result.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )

        course_run = factories.CourseRunFactory(
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            resource_link=resource_link,
        )

        enrollment = factories.EnrollmentFactory(course_run=course_run)

        self.assertIs(enrollment.is_passed, True)
        mock_get_grades.assert_called_once_with(
            username=enrollment.user.username, resource_link=course_run.resource_link
        )

        # - Call it again should return the same result
        mock_get_grades.reset_mock()
        self.assertIs(enrollment.is_passed, True)
        # - But `get_grades` should not have been called again
        mock_get_grades.assert_not_called()

    @override_settings(JOANIE_ENROLLMENT_GRADE_CACHE_TTL=600)
    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    @mock.patch.object(OpenEdXLMSBackend, "get_grades", side_effect=GradeError())
    def test_models_enrollment_is_passed_not_cached_on_failure(
        self, mock_get_grades, _
    ):
        """
        In case of get_grades LMS request fails, `is_passed` property should be False
        and the result should not be cached.
        """
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )

        course_run = factories.CourseRunFactory(
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            resource_link=resource_link,
        )

        enrollment = factories.EnrollmentFactory(course_run=course_run)

        self.assertIs(enrollment.is_passed, False)

        mock_get_grades.assert_called_once_with(
            username=enrollment.user.username, resource_link=course_run.resource_link
        )

        # - Calling it again should trigger the `get_grades` method
        mock_get_grades.reset_mock()
        mock_get_grades.return_value = {"passed": True}
        mock_get_grades.side_effect = None
        self.assertIs(enrollment.is_passed, True)
        mock_get_grades.assert_called_once_with(
            username=enrollment.user.username, resource_link=course_run.resource_link
        )
