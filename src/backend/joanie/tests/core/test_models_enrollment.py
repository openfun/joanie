"""
Test suite for enrollment models
"""

from datetime import timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from joanie.core import factories
from joanie.core.exceptions import EnrollmentError, GradeError
from joanie.core.models import CourseState, Enrollment
from joanie.lms_handler.backends.moodle import MoodleLMSBackend
from joanie.lms_handler.backends.openedx import OpenEdXLMSBackend


@override_settings(
    JOANIE_LMS_BACKENDS=[
        {
            "API_TOKEN": "a_secure_api_token",
            "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
            "BASE_URL": "http://moodle.test/webservice/rest/server.php",
            "COURSE_REGEX": r"^.*/course/view.php\?id=.*$",
            "SELECTOR_REGEX": r"^.*/course/view.php\?id=.*$",
        },
        {
            "API_TOKEN": "FakeEdXAPIKey",
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "BASE_URL": "http://edx:8073",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            "SELECTOR_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
        },
    ]
)
# pylint: disable=too-many-public-methods
class EnrollmentModelsTestCase(TestCase):
    """Test suite for the Enrollment model."""

    maxDiff = None

    def setUp(self):
        super().setUp()
        self.now = timezone.now()

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    def test_models_enrollment_str_active(self, _mock_set):
        """The string representation should work as expected for an active enrollment."""
        resource_link = (
            "http://openedx.test/courses/course-v1:edx+000001+Demo_Course/course"
        )

        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
            title="my run",
            resource_link=resource_link,
            is_listed=True,
        )

        enrollment = factories.EnrollmentFactory(
            course_run=course_run,
            user__username="Françoise",
            is_active=True,
            state="set",
        )

        self.assertEqual(
            str(enrollment),
            f"[active][set] Françoise for my run [{course_run.state['text']}]",
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", side_effect=EnrollmentError)
    def test_models_enrollment_str_inactive(self, _mock_set):
        """The string representation should work as expected for an inactive enrollment."""
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
            title="my run",
        )

        enrollment = factories.EnrollmentFactory(
            course_run=course_run,
            user__username="Françoise",
            is_active=False,
            state="failed",
        )

        self.assertEqual(
            str(enrollment),
            f"[inactive][failed] Françoise for my run [{course_run.state['text']}]",
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    def test_models_enrollment_unique_course_run_user(self, _mock_set):
        """
        A user can only have one enrollment on a given course run.
        """
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=False)

        with self.assertRaises(ValidationError) as context:
            Enrollment.objects.create(
                course_run=enrollment.course_run,
                user=enrollment.user,
                is_active=True,
            )

        self.assertEqual(
            "{'__all__': ['Enrollment with this Course run and User already exists.']}",
            str(context.exception),
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    def test_models_enrollment_unique_opened_course_run_per_course_and_user(
        self, _mock_set
    ):
        """
        A user can only have one enrollment for an opened course run for a course.
        """
        [cr1, cr2] = factories.CourseRunFactory.create_batch(
            2,
            state=CourseState.ONGOING_OPEN,
            course=factories.CourseFactory(),
            is_listed=True,
        )
        enrollment = factories.EnrollmentFactory(course_run=cr1, is_active=True)

        with self.assertRaises(ValidationError) as context:
            Enrollment.objects.create(
                course_run=cr2, user=enrollment.user, is_active=True
            )

        self.assertEqual(
            (
                "{'user': ['You are already enrolled to an opened course run "
                f'for the course "{cr2.course.title}".\']}}'
            ),
            str(context.exception),
        )

        enrollment.is_active = False
        enrollment.save()

        # If the first enrollment is not active anymore, user should be able to enroll
        # to another course run for the same course
        Enrollment.objects.create(course_run=cr2, user=enrollment.user, is_active=True)

        # And finally it should not be able to re-enroll to the first course run
        with self.assertRaises(ValidationError) as context:
            enrollment.is_active = True
            enrollment.save()

        self.assertEqual(
            (
                "{'user': ['You are already enrolled to an opened course run "
                f'for the course "{cr1.course.title}".\']}}'
            ),
            str(context.exception),
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_models_enrollment_not_unique_course_run_per_course_and_user(
        self, _mock_set
    ):
        """
        A user can have multiple enrollments for a same course from the moment only one
        is currently opened.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()

        with mock.patch.object(
            timezone, "now", return_value=self.now - timedelta(days=7)
        ):
            # Go back in the past to enroll user to a course run that was opened.
            factories.EnrollmentFactory(
                user=user,
                is_active=True,
                course_run=factories.CourseRunFactory(
                    course=course,
                    start=timezone.now() - timedelta(hours=1),
                    end=timezone.now() + timedelta(hours=2),
                    enrollment_start=timezone.now() - timedelta(hours=2),
                    enrollment_end=timezone.now() + timedelta(hours=1),
                    is_listed=True,
                ),
            )

        # Now create a course run currently opened now
        course_run = factories.CourseRunFactory(
            course=course,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
        )

        # User should be able to enroll to this course run
        factories.EnrollmentFactory(user=user, course_run=course_run, is_active=True)

        # So User should have two active enrollments for the same course
        user.refresh_from_db()
        self.assertEqual(
            user.enrollments.filter(course_run__course=course, is_active=True).count(),
            2,
        )

    def test_models_enrollment_forbid_for_non_listed_course_run(self):
        """If a course run is not listed, user should not be allowed to enroll."""
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )

        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(
                course_run=course_run, was_created_by_order=True, is_active=True
            )

        self.assertEqual(
            "{'__all__': ['You are not allowed to enroll to a course run not listed.']}",
            str(context.exception),
        )

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_models_enrollment_allows_for_non_listed_course_run_with_product(
        self, _mock_set
    ):
        """
        If a course run is not listed but linked to a product,
        user should be allowed to enroll if he/she purchased the product.
        """
        user = factories.UserFactory()
        course_run = factories.CourseRunFactory.create_batch(
            2,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
            course=factories.CourseFactory(),
        )[0]
        product = factories.ProductFactory(
            target_courses=[course_run.course], price="0.00"
        )

        # - Enrollment should be forbid as user does not purchase the product
        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(
                course_run=course_run,
                user=user,
                was_created_by_order=True,
                is_active=True,
            )

        self.assertEqual(
            (
                f"{{'__all__': ['Course run \"{str(course_run.id)}\" "
                "requires a valid order to enroll.']}"
            ),
            str(context.exception),
        )

        # - Once the product purchased, enrollment should be allowed
        order = factories.OrderFactory(owner=user, product=product)
        order.flow.init()
        factories.EnrollmentFactory(
            course_run=course_run, user=user, was_created_by_order=True
        )

    def test_models_enrollment_set_existing(self):
        """Calling the set method is only allowed on an existing enrollment"""
        user = factories.UserFactory()
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
        )
        enrollment = Enrollment(course_run=course_run, user=user)

        with self.assertRaises(ValidationError) as context:
            enrollment.set()

        self.assertEqual(
            "['The enrollment should be created before being set to the LMS.']",
            str(context.exception),
        )
        self.assertEqual(user.enrollments.count(), 0)

    @mock.patch("joanie.core.models.Enrollment.set")
    def test_models_enrollment_set_on_create(self, mock_set):
        """
        When an enrollment is created, the set method should be called to
        create the enrollment on the LMS if this one is active
        """
        factories.EnrollmentFactory(is_active=False)
        mock_set.assert_not_called()

        factories.EnrollmentFactory(is_active=True)
        mock_set.assert_called_once()

    @mock.patch("joanie.core.models.Enrollment.set")
    def test_models_enrollment_set_on_update(self, mock_set):
        """
        When an enrollment is updated, only if the is_active state is
        changed, the method set should be called.
        """
        enrollment = factories.EnrollmentFactory(is_active=True)
        mock_set.assert_called_once()
        mock_set.reset_mock()

        enrollment.is_active = False
        enrollment.save()
        enrollment.refresh_from_db()
        mock_set.assert_called_once()
        mock_set.reset_mock()

        enrollment.is_active = False
        enrollment.save()
        enrollment.refresh_from_db()
        mock_set.assert_not_called()
        mock_set.reset_mock()

        enrollment.is_active = True
        enrollment.save()
        mock_set.assert_called_once()

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment")
    def test_models_enrollment_forbid_for_non_listed_course_run_not_included_in_product(
        self, _mock_set
    ):
        """
        If a course run is not listed and not linked to a product, user should not be
        allowed to enroll to this course run even if he/she purchased the product.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        [cr1, cr2, cr3] = factories.CourseRunFactory.create_batch(
            3,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
            course=course,
        )
        product = factories.ProductFactory(target_courses=[course], price="0.00")

        # - Restrict available course runs for this product to cr1
        course_relation = product.target_course_relations.get(course=course)
        course_relation.course_runs.set([cr1, cr2])

        order = factories.OrderFactory(owner=user, product=product)
        order.flow.init()

        # - Enroll to cr2 should fail
        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(
                course_run=cr3, user=user, was_created_by_order=True, is_active=True
            )

        self.assertEqual(
            (
                f"{{'__all__': ['Course run \"{cr3.id}\" "
                "requires a valid order to enroll.']}"
            ),
            str(context.exception),
        )
        self.assertEqual(user.enrollments.count(), 0)

        # - But user should be allowed to enroll to cr1
        factories.EnrollmentFactory(
            course_run=cr1, user=user, was_created_by_order=True
        )
        self.assertEqual(user.enrollments.count(), 1)

    def test_models_enrollment_allow_to_unenroll_from_closed_course_run(self):
        """
        If a course run is closed, user should be allowed to unenroll.
        """
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
        )

        # - As the course run is opened, enrollment should be allowed
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)

        # - User should be able to unenroll then re-enroll
        enrollment.is_active = False
        enrollment.save()

        enrollment.is_active = True
        enrollment.save()

        # - Now we close the course run
        course_run.enrollment_end = timezone.now() - timedelta(days=1)
        course_run.save()

        # - User should be still able to unenroll
        enrollment.is_active = False
        enrollment.save()

        # - But user should not be able anymore to re-enroll
        enrollment.is_active = True
        with self.assertRaises(ValidationError) as context:
            enrollment.save()

        self.assertDictEqual(
            context.exception.message_dict,
            {
                "__all__": [
                    "You are not allowed to enroll to a course run not opened for enrollment."
                ]
            },
        )

    def test_models_enrollment_forbid_for_closed_course_run(self):
        """If a course run is closed, user should not be allowed to enroll."""
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_CLOSED,
        )

        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(course_run=course_run)

        self.assertEqual(
            (
                "{'__all__': ["
                "'You are not allowed to enroll to a course run not"
                " opened for enrollment.']}"
            ),
            str(context.exception),
        )

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
        course_run = factories.CourseRunFactory.create(
            state=CourseState.ONGOING_OPEN,
            resource_link=resource_link,
            is_listed=True,
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
        course_run = factories.CourseRunFactory.create(
            state=CourseState.ONGOING_OPEN,
            resource_link=resource_link,
            is_listed=True,
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

    @mock.patch.object(OpenEdXLMSBackend, "set_enrollment", return_value=True)
    def test_models_enrollment_was_created_by_order_flag(self, _mock_set):
        """
        For a course run which is listed (available for free enrollment) and also
        linked to a product, the `was_created_by_order` flag can be set to store
        the creation context of an enrollment. Sets to True if the enrollment has been
        created along an order and False otherwise.
        """

        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory.create_batch(
            2,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
            course=course,
        )[0]
        product = factories.ProductFactory(target_courses=[course], price="0.00")

        user = factories.UserFactory()
        # User can enroll to the course run for free
        enrollment = factories.EnrollmentFactory(
            course_run=course_run, user=user, was_created_by_order=False
        )
        self.assertFalse(enrollment.was_created_by_order)

        # Then if user purchases the product, the flag should not have been updated
        order = factories.OrderFactory(owner=user, product=product)
        order.flow.init()
        order_enrollment = order.get_target_enrollments().first()
        self.assertEqual(enrollment, order_enrollment)
        self.assertFalse(order_enrollment.was_created_by_order)

    @mock.patch.object(MoodleLMSBackend, "set_enrollment", return_value=True)
    def test_models_enrollment_was_created_by_order_flag_moodle(self, _mock_set):
        """
        For a course run which is listed (available for free enrollment) and also
        linked to a product, the `was_created_by_order` flag can be set to store
        the creation context of an enrollment. Sets to True if the enrollment has been
        created along an order and False otherwise.
        """

        course = factories.CourseFactory()
        course_run = factories.CourseRunMoodleFactory.create_batch(
            2,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
            course=course,
        )[0]
        product = factories.ProductFactory(target_courses=[course], price="0.00")

        user = factories.UserFactory()
        # User can enroll to the course run for free
        enrollment = factories.EnrollmentFactory(
            course_run=course_run, user=user, was_created_by_order=False
        )
        self.assertFalse(enrollment.was_created_by_order)

        # Then if user purchases the product, the flag should not have been updated
        order = factories.OrderFactory(owner=user, product=product)
        order.flow.init()
        order_enrollment = order.get_target_enrollments().first()
        self.assertEqual(enrollment, order_enrollment)
        self.assertFalse(order_enrollment.was_created_by_order)

    def test_models_enrollment_forbid_for_non_listed_course_out_of_scope_of_order(
        self,
    ):
        """
        If a user tries to enroll to a non-listed course run out of scope of an order,
        a ValidationError should be raised.
        """
        course_run = factories.CourseRunFactory.create(
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )
        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(
                course_run=course_run, was_created_by_order=False, is_active=True
            )

        self.assertEqual(
            str(context.exception),
            (
                "{'was_created_by_order': ["
                "'You cannot enroll to a non-listed course run "
                "out of the scope of an order.']}"
            ),
        )

    def test_models_enrollment_forbid_for_listed_course_run_not_linked_to_product_in_scope_of_order(  # pylint: disable=line-too-long
        self,
    ):
        """
        If a user tries to enroll to a listed course run which is not linked to a
        product in the scope of an order, a ValidationError should be raised.
        """
        course_run = factories.CourseRunFactory.create(
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
        )

        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(
                course_run=course_run, was_created_by_order=True, is_active=True
            )

        self.assertEqual(
            str(context.exception),
            (
                "{'was_created_by_order': ["
                "'The related course run is not linked to any product, so it cannot be "
                "created in the scope of an order.']}"
            ),
        )

    def test_models_enrollment_forbid_for_listed_course_run_linked_to_product_require_contract(  # pylint: disable=line-too-long
        self,
    ):
        """
        If a user tries to enroll to a not listed course run which is linked to a
        product requiring to sign a contract and that user has not signed this contract
        yet, a ValidationError should be raised.
        """
        course_run = factories.CourseRunFactory.create(
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )

        factories.CourseRunFactory.create(
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
            course=course_run.course,
        )

        product = factories.ProductFactory(
            contract_definition=factories.ContractDefinitionFactory(),
            target_courses=[course_run.course],
            price="0.00",
        )

        relation = factories.CourseProductRelationFactory(product=product)

        order = factories.OrderFactory(
            product=product,
            course=relation.course,
            organization=relation.organizations.first(),
        )
        order.flow.init()

        factories.ContractFactory(
            order=order,
            definition=product.contract_definition,
        )

        with self.assertRaises(ValidationError) as context:
            factories.EnrollmentFactory(
                course_run=course_run,
                was_created_by_order=True,
                is_active=True,
                user=order.owner,
            )

        self.assertEqual(order.owner.enrollments.count(), 0)
        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ["
                f"'Course run \"{course_run.id}\" requires a valid order to enroll.']}}"
            ),
        )

        # - Recreate a signed contract for the order
        order.contract.delete()
        factories.ContractFactory(
            order=order,
            definition=product.contract_definition,
            submitted_for_signature_on=timezone.now(),
            student_signed_on=timezone.now(),
        )

        # - Now the enrollment should be allowed
        factories.EnrollmentFactory(
            course_run=course_run,
            was_created_by_order=True,
            is_active=True,
            user=order.owner,
        )

        self.assertEqual(order.owner.enrollments.count(), 1)
