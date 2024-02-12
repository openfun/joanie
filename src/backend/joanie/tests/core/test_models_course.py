"""
Test suite for course models
"""
from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from joanie.core import factories, models
from joanie.core.models import MAX_DATE, CourseState
from joanie.tests.base import BaseAPITestCase


class CourseModelsTestCase(BaseAPITestCase):
    """Test suite for the Course model."""

    def test_models_course_fields_code_normalize(self):
        """The `code` field should be normalized to an ascii slug on save."""
        course = factories.CourseFactory()

        course.code = "Là&ça boô"
        course.save()
        self.assertEqual(course.code, "LACA-BOO")

    def test_models_course_effort_duration_field(self):
        """
        The duration field effort must accept timedelta values when instanciated.
        """
        course = factories.CourseFactory(effort=timedelta(seconds=3600))

        self.assertEqual(models.Course.objects.count(), 1)
        self.assertEqual(type(course.effort), timedelta)

    def test_models_course_effort_duration_field_accepts_iso8601_value(self):
        """
        It should be possible to set an ISO 8601 value representing 10 hours into the
        effort DurationField when instanciating a new object Course.
        """
        course = factories.CourseFactory(effort="PT10H")  # represents 10 hours

        self.assertEqual(models.Course.objects.count(), 1)
        self.assertEqual(course.effort, timedelta(seconds=36000))
        self.assertEqual(type(course.effort), timedelta)

    def test_models_course_effort_duration_field_querying(self):
        """
        We should be able to compare two courses with different effort duration values.
        Allowing us to filter through queryset on Course through the effort field.
        """
        course_1 = factories.CourseFactory(effort=timedelta(seconds=3700))
        course_2 = factories.CourseFactory(effort=timedelta(seconds=3600))

        self.assertGreater(course_1.effort, course_2.effort)
        self.assertEqual(
            models.Course.objects.filter(effort__gte=timedelta(seconds=3500)).count(), 2
        )
        self.assertEqual(
            models.Course.objects.filter(effort__lte=timedelta(seconds=3699)).count(), 1
        )
        self.assertEqual(
            models.Course.objects.filter(effort=timedelta(seconds=3600)).count(), 1
        )

    def test_models_course_fields_code_unique(self):
        """The `code` field should be unique among courses."""
        factories.CourseFactory(code="the-unique-code")

        # Creating a second course with the same code should raise an error...
        with self.assertRaises(ValidationError) as context:
            factories.CourseFactory(code="the-unique-code")

        self.assertEqual(
            context.exception.messages[0], "Course with this Code already exists."
        )
        self.assertEqual(
            models.Course.objects.filter(code="THE-UNIQUE-CODE").count(), 1
        )

    def test_models_course_delete(self):
        """
        Confirm course can't be deleted if it has course runs.
        """
        course_run = factories.CourseRunFactory()
        course = factories.CourseFactory(course_runs=[course_run])

        with self.assertRaises(ProtectedError):
            course.delete()

    # get_abilities

    def test_models_course_get_abilities_anonymous(self):
        """Check abilities returned for an anonymous user."""
        course = factories.CourseFactory()
        abilities = course.get_abilities(AnonymousUser())

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
            },
        )

    def test_models_course_get_abilities_authenticated(self):
        """Check abilities returned for an authenticated user."""
        course = factories.CourseFactory()
        abilities = course.get_abilities(factories.UserFactory())
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
            },
        )

    def test_models_course_get_abilities_owner(self):
        """Check abilities returned for the owner of a course."""
        access = factories.UserCourseAccessFactory(role="owner")
        abilities = access.course.get_abilities(access.user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "manage_accesses": True,
            },
        )

    def test_models_course_get_abilities_administrator(self):
        """Check abilities returned for the administrator of a course."""
        access = factories.UserCourseAccessFactory(role="administrator")
        abilities = access.course.get_abilities(access.user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": True,
                "put": True,
                "manage_accesses": True,
            },
        )

    def test_models_course_get_abilities_instructor(self):
        """Check abilities returned for the instructor of a course."""
        access = factories.UserCourseAccessFactory(role="instructor")
        abilities = access.course.get_abilities(access.user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
            },
        )

    def test_models_course_get_abilities_manager_user(self):
        """Check abilities returned for the manager of a course."""
        access = factories.UserCourseAccessFactory(role="manager")

        with self.assertNumQueries(1):
            abilities = access.course.get_abilities(access.user)

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
            },
        )

    def test_models_course_get_abilities_preset_role(self):
        """No query is done if the role is preset e.g. with query annotation."""
        access = factories.UserCourseAccessFactory(role="manager")
        access.course.user_role = "manager"

        with self.assertNumQueries(0):
            abilities = access.course.get_abilities(access.user)

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
            },
        )


class CourseStateModelsTestCase(TestCase):
    """
    Unit test suite for computing a date to display on the course glimpse depending on the state
    of its related course runs:
        0: a run is ongoing and open for enrollment > "closing on": {enrollment_end}
        1: a run is future and open for enrollment > "starting on": {start}
        2: a run is future and not yet open or already closed for enrollment >
        "starting on": {start}
        3: a run is ongoing but closed for enrollment > "on going": {None}
        4: there's a finished run in the past > "archived": {None}
        5: there are no runs at all > "coming soon": {None}
    """

    def setUp(self):
        super().setUp()
        self.now = timezone.now()

    def test_models_course_state_to_be_scheduled(self):
        """
        Confirm course state result when there is no course runs at all.
        """
        course = factories.CourseFactory()
        with self.assertNumQueries(2):
            state = course.state
        self.assertEqual(state, CourseState(7))

    def test_models_course_state_archived_closed(self):
        """
        Confirm course state when there is a course run only in the past.
        """
        course = factories.CourseFactory()
        factories.CourseRunFactory(
            course=course,
            state=CourseState.ARCHIVED_CLOSED,
        )
        with self.assertNumQueries(2):
            state = course.state
        self.assertEqual(state, CourseState(6))

    def test_models_course_state_archived_open(self):
        """
        Confirm course state when there is a past course run but open for enrollment.
        """
        course = factories.CourseFactory()
        factories.CourseRunFactory(
            course=course,
            state=CourseState.ARCHIVED_OPEN,
        )
        with self.assertNumQueries(2):
            state = course.state
        self.assertEqual(state, CourseState(2, MAX_DATE))

    def test_models_course_state_ongoing_enrollment_closed(self):
        """
        Confirm course state when there is an ongoing course run but closed for
        enrollment.
        """
        course = factories.CourseFactory()
        factories.CourseRunFactory(
            course=course,
            state=CourseState.ONGOING_CLOSED,
        )
        with self.assertNumQueries(2):
            state = course.state
        self.assertEqual(state, CourseState(5))

    def test_models_course_state_future_enrollment_not_yet_open(self):
        """
        Confirm course state when there is a future course run but not yet open for
        enrollment.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            course=course,
            state=CourseState.FUTURE_NOT_YET_OPEN,
        )
        with self.assertNumQueries(2):
            state = course.state
        expected_state = CourseState(3, course_run.start)
        self.assertEqual(state, expected_state)

    def test_models_course_state_future_enrollment_closed(self):
        """
        Confirm course state when there is a future course run but closed for
        enrollment.
        """
        course = factories.CourseFactory()
        factories.CourseRunFactory(
            course=course,
            state=CourseState.FUTURE_CLOSED,
        )
        with self.assertNumQueries(2):
            state = course.state
        expected_state = CourseState(4)
        self.assertEqual(state, expected_state)

    def test_models_course_state_future_enrollment_open(self):
        """
        Confirm course state when there is a future course run open for enrollment.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            course=course,
            state=CourseState.FUTURE_OPEN,
        )
        with self.assertNumQueries(2):
            state = course.state
        expected_state = CourseState(1, course_run.start)
        self.assertEqual(state, expected_state)

    def test_models_course_state_ongoing_open(self):
        """
        Confirm course state when there is an ongoing course run open for enrollment.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            course=course,
            state=CourseState.ONGOING_OPEN,
        )
        with self.assertNumQueries(1):
            state = course.state
        expected_state = CourseState(0, course_run.enrollment_end)
        self.assertEqual(state, expected_state)

    def test_models_course_state_with_products(self):
        """
        Confirm course state takes course's products in account
        """
        target_course = factories.CourseFactory()
        target_course_run = factories.CourseRunFactory(
            course=target_course,
            state=CourseState.ONGOING_OPEN,
        )
        product = factories.ProductFactory(target_courses=[target_course])
        course = factories.CourseFactory(products=[product])

        with self.assertNumQueries(3):
            state = course.state

        expected_state = CourseState(0, target_course_run.enrollment_end)
        self.assertEqual(state, expected_state)

    def test_models_course_get_selling_organizations_all(self):
        """
        The method `get_selling_organizations` should return all organizations
        included in product_relations of the course.
        """

        course = factories.CourseFactory()
        organization = factories.OrganizationFactory()
        factories.CourseProductRelationFactory.create_batch(
            2, course=course, organizations=[organization]
        )

        organizations = course.get_selling_organizations()

        with self.assertNumQueries(1):
            self.assertEqual(organizations.count(), 1)

    def test_models_course_get_selling_organizations_with_product(self):
        """
        The method `get_selling_organizations` should return all organizations
        included in product_relations of the course and a provided product.
        """

        course = factories.CourseFactory()
        product = factories.ProductFactory()
        factories.CourseProductRelationFactory(
            course=course,
            organizations=factories.OrganizationFactory.create_batch(1),
        )
        factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )

        organizations = course.get_selling_organizations(product=product)

        with self.assertNumQueries(1):
            self.assertEqual(organizations.count(), 2)
