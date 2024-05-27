"""Test suite for course run utility methods."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone as django_timezone

from joanie.core import enums, factories, models
from joanie.core.utils.course_run import get_course_run_metrics


class UtilsCourseRunTestCase(TestCase):
    """Test suite for course run utility methods."""

    def test_utils_course_run_with_non_existing_resource_link_parameter(self):
        """
        Test the scenario when a non existent `resource_link` is parsed as input.
        It should raise a 'ValidationError' mentionning to provide an existing `resource_link`
        of a course run that has ended.
        """
        with self.assertRaises(ValidationError) as context:
            get_course_run_metrics(resource_link="http://opendex.test/fake_course_run")

        self.assertEqual(
            str(context.exception),
            "['Make sure to give an existing resource link from an ended course run.']",
        )

    def test_utils_course_run_where_student_enrolls_and_does_not_make_an_order_to_get_certificate(
        self,
    ):
        """
        Test the scenario where a student enrolls to a course run that is open for enrollment,
        and he does not buy the access to get the certificate at the end of the course.
        The ouput must indicate that there was 1 enrollment made and 0 order to have access
        to the certificate.
        """
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=factories.CourseFactory(),
            state=models.CourseState.ONGOING_OPEN,
            languages="fr",
            resource_link="http://openedx.test/courses/course-v1:edx+00000+0/course/",
        )
        # Set an enrollment for the course run
        factories.EnrollmentFactory(course_run=course_run, is_active=True)
        # Close the course run enrollments and set the end date to have "archived" state
        closing_date = django_timezone.now() - timedelta(days=1)
        course_run.enrollment_end = closing_date
        course_run.end = closing_date
        course_run.save()

        self.assertEqual(
            get_course_run_metrics(resource_link=course_run.resource_link),
            {
                "nb_active_enrollments": 1,
                "nb_validated_certificate_orders": 0,
            },
        )

    def test_utils_course_run_where_student_enrolls_and_makes_an_order_to_access_to_certificate(
        self,
    ):
        """
        Test the scenario where a student enrolls to a course run that is open for enrollment,
        then he decides to unlock the access to get the certificate before the course run
        has ended. The ouput must indicate that there was 1 enrollment made and 1 order to
        have access to the certificate.
        """
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=factories.CourseFactory(),
            state=models.CourseState.ONGOING_OPEN,
            languages="fr",
            resource_link="http://openedx.test/courses/course-v1:edx+00000+0/course/",
        )
        # Set an enrollment
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        # Prepare the order and set it to 'validated' state
        factories.OrderFactory(
            owner=enrollment.user,
            enrollment=enrollment,
            course=None,
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            product__courses=[enrollment.course_run.course],
            state=enums.ORDER_STATE_COMPLETED,
        )
        # Close the course run enrollments and set the end date to have "archived" state
        closing_date = django_timezone.now() - timedelta(days=1)
        course_run.enrollment_end = closing_date
        course_run.end = closing_date
        course_run.save()

        self.assertEqual(
            get_course_run_metrics(resource_link=course_run.resource_link),
            {
                "nb_active_enrollments": 1,
                "nb_validated_certificate_orders": 1,
            },
        )
