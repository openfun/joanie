"""
Test suite for order models
"""

import random
from datetime import datetime, timedelta, timezone
from unittest import mock
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone as django_timezone

from joanie.core import enums, factories
from joanie.core.factories import CourseRunFactory
from joanie.core.models import CourseRun, CourseState, Enrollment

# pylint: disable=too-many-public-methods


class CourseRunModelsTestCase(TestCase):
    """Test suite for the CourseRun model."""

    def setUp(self):
        super().setUp()
        self.now = django_timezone.now()

    def test_models_course_run_string_representation(self):
        """
        The string representation of a course run should be built with its title
        and its state text.
        """

        course_run = factories.CourseRunFactory()
        self.assertEqual(str(course_run), f"{course_run.title} [{course_run.state}]")

    def test_models_course_run_normalized(self):
        """
        The resource_link field should be normalized on save.
        """
        course_run = factories.CourseRunFactory()
        course_run.resource_link = "https://www.Example.Com:443/Capitalized-Path"
        course_run.save()
        self.assertEqual(
            course_run.resource_link, "https://www.example.com/Capitalized-Path"
        )

    def test_models_course_run_uri(self):
        """
        CourseRun instance should have a property `uri`
        that returns the API url to get instance detail.
        """
        course_run = factories.CourseRunFactory()

        self.assertEqual(
            course_run.uri,
            f"https://example.com/api/v1.0/course-runs/{course_run.id}/",
        )

    def test_models_course_run_dates_not_required(self):
        """
        Course run dates are not required.
        """
        course_run = factories.CourseRunFactory(
            start=None, end=None, enrollment_start=None, enrollment_end=None
        )
        for field in ["start", "end", "enrollment_start", "enrollment_end"]:
            self.assertIsNone(getattr(course_run, field))

    def test_models_course_run_unique(self):
        """The resource link field should be unique."""
        course_run = factories.CourseRunFactory()

        with self.assertRaises(ValidationError) as context:
            CourseRun.objects.create(
                course=course_run.course,
                languages=course_run.languages,
                resource_link=course_run.resource_link,
            )

        self.assertEqual(
            "{'resource_link': ['Course run with this Resource link already exists.']}",
            str(context.exception),
        )

    def test_models_course_run_state_start_to_be_scheduled(self):
        """
        A course run that has no start date should return a state with priority 6
        and "to be scheduled" as text.
        """
        course_run = CourseRunFactory(start=None)
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 7,
                "text": "to be scheduled",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_state_enrollment_start_to_be_scheduled(self):
        """
        A course run that has no enrollment start date should return a state with priority 6
        and "to be scheduled" as text.
        """
        course_run = CourseRunFactory(enrollment_start=None)
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 7,
                "text": "to be scheduled",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_state_no_end_date(self):
        """
        A course run with no end date is deemed to be forever on-going.
        """
        course_run = CourseRunFactory(end=None)

        # The course run should be open during its enrollment period
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.enrollment_start.timestamp()) + 1,
                int(course_run.enrollment_end.timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertIn(dict(state)["priority"], [0, 1])

        # The course run should be on-going at any date after its end of enrollment
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.enrollment_end.timestamp()),
                int(datetime(9999, 12, 31).timestamp()),
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 5,
                "text": "on-going",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_state_no_enrollment_end(self):
        """
        A course run that has no end of enrollment is deemed to be always open.
        """
        course_run = CourseRunFactory(enrollment_end=None)

        # The course run should be open between its start of enrollment and its start
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.enrollment_start.timestamp()) + 1,
                int(course_run.start.timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 1,
                "text": "starting on",
                "call_to_action": "enroll now",
                "datetime": course_run.start,
            },
        )

        # The course run should be on-going & open between its start and its end
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.start.timestamp()) + 1,
                int(course_run.end.timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 0,
                "text": "forever open",
                "call_to_action": "enroll now",
                "datetime": None,
            },
        )

        # The course run should be archived open after its end
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.end.timestamp()) + 1,
                int(datetime(9999, 12, 31).timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 2,
                "text": "forever open",
                "call_to_action": "study now",
                "datetime": None,
            },
        )

    def test_models_course_run_state_forever_open(self):
        """
        A course run that has no end of enrollement and no end should be forever open.
        """
        course_run = CourseRunFactory(enrollment_end=None, end=None)

        # The course run should be open between its start of enrollment and its start
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.enrollment_start.timestamp()) + 1,
                int(course_run.start.timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 1,
                "text": "starting on",
                "call_to_action": "enroll now",
                "datetime": course_run.start,
            },
        )

        # The course run should be on-going & open forever after its start
        now = datetime.utcfromtimestamp(
            random.randrange(
                int(course_run.start.timestamp()) + 1,
                int(datetime(9999, 12, 31).timestamp()) - 1,
            )
        ).replace(tzinfo=timezone.utc)

        with mock.patch.object(django_timezone, "now", return_value=now):
            state = course_run.state

        self.assertEqual(
            dict(state),
            {
                "priority": 0,
                "text": "forever open",
                "call_to_action": "enroll now",
                "datetime": None,
            },
        )

    def test_models_course_run_state_archived_open_closing_on(self):
        """
        A course run that is passed and has an enrollment end in the future should return
        a state with priority 2 and "closing on" as text.
        """
        course_run = CourseRunFactory(
            state=CourseState.ARCHIVED_OPEN,
            enrollment_end=django_timezone.now() + timedelta(days=1),
        )
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 2,
                "text": "closing on",
                "call_to_action": "study now",
                "datetime": course_run.enrollment_end,
            },
        )

    def test_models_course_run_state_archived_open_forever_open(self):
        """
        A course run that is passed and has no enrollment end should return
        a state with priority 2 and "forever open" as text.
        """
        course_run = CourseRunFactory(state=CourseState.ARCHIVED_OPEN)
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 2,
                "text": "forever open",
                "call_to_action": "study now",
                "datetime": None,
            },
        )

    def test_models_course_run_state_archived_closed(self):
        """
        A course run that is passed should return a state with priority 6 and "archived"
        as text.
        """
        course_run = CourseRunFactory(state=CourseState.ARCHIVED_CLOSED)
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 6,
                "text": "archived",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_state_ongoing_open(self):
        """
        A course run that is on-going and open for enrollment should return a state with a CTA
        to enroll and the date of the end of enrollment.
        """
        course_run = CourseRunFactory(state=CourseState.ONGOING_OPEN)
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 0,
                "text": "closing on",
                "call_to_action": "enroll now",
                "datetime": course_run.enrollment_end,
            },
        )

    def test_models_course_run_state_ongoing_closed(self):
        """
        A course run that is on-going but closed for enrollment should return a state with
        "on-going" as text and no CTA.
        """
        course_run = CourseRunFactory(state=CourseState.ONGOING_CLOSED)
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 5,
                "text": "on-going",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_state_future_not_open(self):
        """
        A course run that is future and not yet open for enrollment should return a state
        with a CTA to see details with the start date.
        """
        course_run = CourseRunFactory(state=CourseState.FUTURE_NOT_YET_OPEN)
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 3,
                "text": "starting on",
                "call_to_action": None,
                "datetime": course_run.start,
            },
        )

    def test_models_course_run_state_future_open(self):
        """
        A course run that is future and open for enrollment should return a state with a CTA
        to enroll and the start date.
        """
        course_run = CourseRunFactory(state=CourseState.FUTURE_OPEN)
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 1,
                "text": "starting on",
                "call_to_action": "enroll now",
                "datetime": course_run.start,
            },
        )

    def test_models_course_run_state_future_closed(self):
        """
        A course run that is future and already closed for enrollment should return a state
        with "enrollment closed" as text and no CTA.
        """
        course_run = CourseRunFactory(state=CourseState.FUTURE_CLOSED)
        self.assertEqual(
            dict(course_run.state),
            {
                "priority": 4,
                "text": "enrollment closed",
                "call_to_action": None,
                "datetime": None,
            },
        )

    def test_models_course_run_validation_on_update(self):
        """
        When the course field of a course run instance is updated,
        a ValidationError should be raised it the course run instance relies on
        product/order relation.
        """
        course_run = factories.CourseRunFactory()
        product = factories.ProductFactory(target_courses=[course_run.course])

        # - Link course run to the product course relation
        relation = product.target_course_relations.first()
        relation.course_runs.add(course_run)

        # - Try to update the course of the course run
        course_run.course = factories.CourseFactory()
        with self.assertRaises(ValidationError) as context:
            course_run.save()

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ['This course run relies on a product relation. "
                "So you cannot modify its course.']}"
            ),
        )

    def test_model_course_run_get_serialized(self):
        """
        Test the get_serialized method of the CourseRun model.
        catalog_visibility is set to hidden if the course run is not listed
        """
        course_run = factories.CourseRunFactory(
            is_listed=True,
            start=datetime(2022, 6, 6, 6, 0, tzinfo=ZoneInfo("UTC")),
            end=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_end=datetime(2022, 9, 9, 9, 0, tzinfo=ZoneInfo("UTC")),
        )
        self.assertEqual(
            course_run.get_serialized(),
            {
                "course": course_run.course.code,
                "resource_link": f"https://example.com/api/v1.0/course-runs/{course_run.id!s}/",
                "start": "2022-06-06T06:00:00+00:00",
                "end": "2022-07-07T07:00:00+00:00",
                "enrollment_start": "2022-08-08T08:00:00+00:00",
                "enrollment_end": "2022-09-09T09:00:00+00:00",
                "languages": course_run.languages,
                "catalog_visibility": "course_and_search",
                "certificate_offer": None,
                "certificate_price": None,
                "certificate_discounted_price": None,
                "certificate_discount": None,
            },
        )
        course_run.is_listed = False
        course_run.save()
        self.assertEqual(
            course_run.get_serialized(),
            {
                "course": course_run.course.code,
                "resource_link": f"https://example.com/api/v1.0/course-runs/{course_run.id!s}/",
                "start": "2022-06-06T06:00:00+00:00",
                "end": "2022-07-07T07:00:00+00:00",
                "enrollment_start": "2022-08-08T08:00:00+00:00",
                "enrollment_end": "2022-09-09T09:00:00+00:00",
                "languages": course_run.languages,
                "catalog_visibility": "hidden",
                "certificate_offer": None,
                "certificate_price": None,
                "certificate_discounted_price": None,
                "certificate_discount": None,
            },
        )

    def test_model_course_run_get_serialized_hidden(self):
        """
        Test the get_serialized method of the CourseRun model when
        the parameter visibility is set to hidden.
        """
        course_run = factories.CourseRunFactory(
            start=datetime(2022, 6, 6, 6, 0, tzinfo=ZoneInfo("UTC")),
            end=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
            enrollment_end=datetime(2022, 9, 9, 9, 0, tzinfo=ZoneInfo("UTC")),
        )

        self.assertEqual(
            course_run.get_serialized(visibility="hidden"),
            {
                "course": course_run.course.code,
                "resource_link": f"https://example.com/api/v1.0/course-runs/{course_run.id!s}/",
                "start": "2022-06-06T06:00:00+00:00",
                "end": "2022-07-07T07:00:00+00:00",
                "enrollment_start": "2022-08-08T08:00:00+00:00",
                "enrollment_end": "2022-09-09T09:00:00+00:00",
                "languages": course_run.languages,
                "catalog_visibility": "hidden",
                "certificate_offer": None,
                "certificate_price": None,
                "certificate_discounted_price": None,
                "certificate_discount": None,
            },
        )

    def test_model_course_run_get_serialized_course_only(self):
        """
        Test the get_serialized method of the CourseRun model when
        the parameter visibility is set to course_only, catalog_visibility has the right value
        """
        course_run = factories.CourseRunFactory()

        self.assertEqual(
            course_run.get_serialized(visibility="course_only")["catalog_visibility"],
            "course_only",
        )

    def test_model_course_run_get_serialized_with_invalid_visibility(
        self,
    ):
        """
        Test the get_serialized method of the CourseRun model can only have
        expected values for visibility
        """
        course_run = factories.CourseRunFactory()
        with self.assertRaises(ValueError) as context:
            course_run.get_serialized(visibility="invalid_visibility")
            self.assertEqual(
                str(context.exception),
                (
                    "Invalid visibility value. Must be one of : "
                    "COURSE_AND_SEARCH, COURSE_ONLY, HIDDEN"
                ),
            )

    def test_models_course_run_user_can_not_enroll_because_is_already_enrolled_to_the_course(
        self,
    ):
        """
        Test that the user cannot enroll to the course of that course run because he is
        already enrolled to that course in another course run.
        """
        user = factories.UserFactory()
        target_course = factories.CourseFactory()
        course_run_1 = CourseRunFactory(
            course=target_course,
            state=CourseState.ONGOING_OPEN,
        )
        course_run_2 = CourseRunFactory(
            course=target_course,
            state=CourseState.ONGOING_OPEN,
        )
        # Make a free product for the order
        product = factories.ProductFactory(target_courses=[target_course], price="0.00")
        order = factories.OrderFactory(owner=user, product=product)
        order.init_flow()
        factories.EnrollmentFactory(
            user=user,
            course_run=course_run_1,
            is_active=True,
            was_created_by_order=True,
        )
        # User should not be able to enroll to course_run_2 because he is already
        # enrolled to that same course in course_run_1
        self.assertFalse(course_run_2.can_enroll(user))

    def test_models_course_run_user_can_enroll_because_old_course_run_is_closed_already(
        self,
    ):
        """
        Test that the user can enroll in the course of a new course run on a new product,
        even if the user was previously enrolled to the same course through a different course run
        from another product that recently closed for enrollments.
        """
        user = factories.UserFactory()
        target_course = factories.CourseFactory()
        # Course run 1 with target course is opened
        now = django_timezone.now()
        end_date = now + timedelta(days=10)
        course_run_1 = CourseRunFactory(
            course=target_course,
            state=CourseState.ONGOING_OPEN,
            start=now,
            end=end_date,
        )
        product_1 = factories.ProductFactory(
            target_courses=[target_course], price="0.00"
        )
        order_1 = factories.OrderFactory(owner=user, product=product_1)
        order_1.init_flow()
        enrollment = factories.EnrollmentFactory(
            user=user,
            course_run=course_run_1,
            is_active=True,
            was_created_by_order=True,
        )
        # Close the course run 1 for enrollments
        past_end_date = end_date - timedelta(days=5)
        course_run_1.end = past_end_date
        course_run_1.save()
        # Create second course run with same course but opened for enrollments
        course_run_2 = CourseRunFactory(
            course=target_course,
            state=CourseState.ONGOING_OPEN,
            start=now,
            end=end_date + timedelta(days=30),
        )
        product_2 = factories.ProductFactory(
            target_courses=[target_course], price="0.00"
        )
        order_2 = factories.OrderFactory(owner=user, product=product_2)
        order_2.init_flow()
        # Disactivate previous enrollment
        enrollment.is_active = False
        enrollment.save()

        # Mocked that timezone.now() returns a date superior to course_run_1 end date.
        mocked_now = django_timezone.now() + timedelta(days=10)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            can_enroll_to_opened_course_run = course_run_2.can_enroll(user)

        self.assertTrue(can_enroll_to_opened_course_run)

    def test_models_course_run_user_with_no_enrollment_can_enroll(self):
        """
        Test that a user that has no enrollment yet, can enroll to an opened course run.
        """
        user = factories.UserFactory()
        course_run = factories.CourseRunFactory()

        self.assertTrue(course_run.can_enroll(user))
        self.assertEqual(Enrollment.objects.count(), 0)

    def test_models_course_run_get_certificate_offer_none(self):
        """
        Test the get_certificate_offer method of the CourseRun model.
        If no certificate product is related to the course, the course run should have
        no offer.
        """
        course_run = factories.CourseRunFactory()
        self.assertEqual(course_run.get_certificate_offer(), None)

    def test_models_course_run_get_certificate_offer_none_with_credential_product(self):
        """
        Test the get_certificate_offer method of the CourseRun model.
        If no certificate product is related to the course, the course run should have
        no offer.
        """
        course_run = factories.CourseRunFactory()
        factories.ProductFactory(
            courses=[course_run.course],
            type=enums.PRODUCT_TYPE_CREDENTIAL,
        )
        self.assertEqual(course_run.get_certificate_offer(), None)

    def test_models_course_run_get_certificate_offer_free(self):
        """
        Test the get_certificate_offer method of the CourseRun model.
        If a free certificate product is linked to the course, the course run should have
        a free offer.
        """
        course_run = factories.CourseRunFactory()
        factories.ProductFactory(
            courses=[course_run.course], type=enums.PRODUCT_TYPE_CERTIFICATE, price=0
        )
        self.assertEqual(course_run.get_certificate_offer(), enums.COURSE_OFFER_FREE)

    def test_models_course_run_get_certificate_offer_paid(self):
        """
        Test the get_certificate_offer method of the CourseRun model.
        If a not free certificate product is linked to the course, the course run should have
        a paid offer.
        """
        course_run = factories.CourseRunFactory()
        factories.ProductFactory(
            courses=[course_run.course],
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            price=42.00,
        )
        self.assertEqual(course_run.get_certificate_offer(), enums.COURSE_OFFER_PAID)
