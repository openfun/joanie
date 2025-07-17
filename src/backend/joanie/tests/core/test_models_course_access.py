"""
Test suite for course access models
"""

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


# pylint: disable=too-many-public-methods
class CourseAccessModelsTestCase(BaseAPITestCase):
    """Test suite for the CourseAccess model."""

    def test_models_course_access_course_user_pair_unique(self):
        """Only one course access object is allowed per course/user pair."""
        access = factories.UserCourseAccessFactory()

        # Creating a second course access for the same course/user pair should raise an error...
        with self.assertRaises(ValidationError) as context:
            factories.UserCourseAccessFactory(course=access.course, user=access.user)

        self.assertEqual(
            context.exception.messages[0],
            "Course access with this Course and User already exists.",
        )
        self.assertEqual(models.CourseAccess.objects.count(), 1)

    # get_abilities

    def test_models_course_access_get_abilities_anonymous(self):
        """Check abilities returned for an anonymous user."""
        access = factories.UserCourseAccessFactory()
        abilities = access.get_abilities(AnonymousUser())

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": False,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_course_access_get_abilities_authenticated(self):
        """Check abilities returned for an authenticated user."""
        access = factories.UserCourseAccessFactory()
        abilities = access.get_abilities(factories.UserFactory())
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": False,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    # - for owner

    def test_models_course_access_get_abilities_for_owner_of_self_allowed(self):
        """
        Check abilities of self access for the owner of a course when there is more
        than one user left.
        """
        access = factories.UserCourseAccessFactory(role="owner")
        factories.UserCourseAccessFactory(
            course=access.course, role="owner"
        )  # another one
        abilities = access.get_abilities(access.user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["administrator", "instructor", "manager"],
            },
        )

    def test_models_course_access_get_abilities_for_owner_of_self_last(self):
        """
        Check abilities of self access for the owner of a course when there is
        only one owner left.
        """
        access = factories.UserCourseAccessFactory(role="owner")
        abilities = access.get_abilities(access.user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_course_access_get_abilities_for_owner_of_owner(self):
        """Check abilities of owner access for the owner of a course."""
        access = factories.UserCourseAccessFactory(role="owner")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="owner"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_course_access_get_abilities_for_owner_of_administrator(self):
        """Check abilities of administrator access for the owner of a course."""
        access = factories.UserCourseAccessFactory(role="administrator")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="owner"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["owner", "instructor", "manager"],
            },
        )

    def test_models_course_access_get_abilities_for_owner_of_instructor(self):
        """Check abilities of instructor access for the owner of a course."""
        access = factories.UserCourseAccessFactory(role="instructor")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="owner"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["owner", "administrator", "manager"],
            },
        )

    def test_models_course_access_get_abilities_for_owner_of_manager(self):
        """Check abilities of manager access for the owner of a course."""
        access = factories.UserCourseAccessFactory(role="manager")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="owner"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["owner", "administrator", "instructor"],
            },
        )

    # - for administrator

    def test_models_course_access_get_abilities_for_administrator_of_owner(self):
        """Check abilities of owner access for the administator of a course."""
        access = factories.UserCourseAccessFactory(role="owner")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="administrator"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_course_access_get_abilities_for_administrator_of_administrator(
        self,
    ):
        """Check abilities of administrator access for the administrator of a course."""
        access = factories.UserCourseAccessFactory(role="administrator")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="administrator"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["instructor", "manager"],
            },
        )

    def test_models_course_access_get_abilities_for_administrator_of_instructor(self):
        """Check abilities of instructor access for the administrator of a course."""
        access = factories.UserCourseAccessFactory(role="instructor")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="administrator"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["administrator", "manager"],
            },
        )

    def test_models_course_access_get_abilities_for_administrator_of_manager(self):
        """Check abilities of manager access for the administrator of a course."""
        access = factories.UserCourseAccessFactory(role="manager")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="administrator"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "set_role_to": ["administrator", "instructor"],
            },
        )

    # - for instructor

    def test_models_course_access_get_abilities_for_instructor_of_owner(self):
        """Check abilities of owner access for the instructor of a course."""
        access = factories.UserCourseAccessFactory(role="owner")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="instructor"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_course_access_get_abilities_for_instructor_of_administrator(self):
        """Check abilities of administrator access for the instructor of a course."""
        access = factories.UserCourseAccessFactory(role="administrator")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="instructor"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_course_access_get_abilities_for_instructor_of_instructor(self):
        """Check abilities of instructor access for the instructor of a course."""
        access = factories.UserCourseAccessFactory(role="instructor")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="instructor"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_course_access_get_abilities_for_instructor_of_manager(self):
        """Check abilities of manager access for the instructor of a course."""
        access = factories.UserCourseAccessFactory(role="manager")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="instructor"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    # - for manager

    def test_models_course_access_get_abilities_for_manager_of_owner(self):
        """Check abilities of owner access for the manager of a course."""
        access = factories.UserCourseAccessFactory(role="owner")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="manager"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_course_access_get_abilities_for_manager_of_administrator(self):
        """Check abilities of administrator access for the manager of a course."""
        access = factories.UserCourseAccessFactory(role="administrator")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="manager"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_course_access_get_abilities_for_manager_of_instructor(self):
        """Check abilities of instructor access for the manager of a course."""
        access = factories.UserCourseAccessFactory(role="instructor")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="manager"
        ).user
        abilities = access.get_abilities(user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_course_access_get_abilities_for_manager_of_manager(self):
        """Check abilities of manager access for the manager of a course."""
        access = factories.UserCourseAccessFactory(role="manager")
        factories.UserCourseAccessFactory(course=access.course)  # another one
        user = factories.UserCourseAccessFactory(
            course=access.course, role="manager"
        ).user

        with self.record_performance():
            abilities = access.get_abilities(user)

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )

    def test_models_course_access_get_abilities_preset_role(self):
        """No query is done if the role is preset e.g. with query annotation."""
        access = factories.UserCourseAccessFactory(role="manager")
        user = factories.UserCourseAccessFactory(
            course=access.course, role="manager"
        ).user
        access.user_role = "manager"

        with self.record_performance():
            abilities = access.get_abilities(user)

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "set_role_to": [],
            },
        )
