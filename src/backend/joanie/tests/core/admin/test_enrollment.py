"""Test suite for admin enrollment viewset search fields."""

from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse

from joanie.core.factories import (
    CourseRunFactory,
    EnrollmentFactory,
    OrganizationFactory,
    UserFactory,
)
from joanie.core.models import CourseState


class EnrollmentAdminTestCase(TestCase):
    """
    Test suite for admin enrollment viewset search fields.
    """

    def setUp(self):
        """
        Set up data for every tests of this class.
        This Enrollment view for the backoffice django requires to select a specific user
        to search through enrollments first.
        """
        # Create admin user who will request
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=self.admin_user.username, password="password")

        # Create organization
        self.organization = OrganizationFactory(title="France Digital University")
        self.organization.translations.create(
            language_code="fr-fr", title="France Université Numérique"
        )
        # Create random enrollments
        EnrollmentFactory.create_batch(2)
        # Create course run and link course to organization
        self.course_run = CourseRunFactory(
            course__organizations=[self.organization],
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
            title="Python for beginners",
            resource_link="https://example.com/python-for-beginners",
            course__code="PY101",
        )
        self.course_run.translations.create(
            language_code="fr-fr", title="Python pour les débutants"
        )
        # Create enrollment with a specific user
        self.user = UserFactory()
        self.enrollment = EnrollmentFactory(
            course_run=self.course_run, user=self.user, is_active=True
        )

    def test_admin_enrollment_changelist_search_by_organization_title(self):
        """
        When we search with an organization title, we should be able to find the enrollment
        that matches the user and the organization title.
        """
        # Prepare url and search parameters
        enrollment_search_url = reverse("admin:core_enrollment_changelist")
        search_parameters = {"q": "Digital", "user__pk__exact": str(self.user.id)}

        response = self.client.get(enrollment_search_url, search_parameters)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed("admin/core/enrollment/change_list.html")
        self.assertContains(response, str(self.enrollment.user))
        self.assertContains(response, str(self.course_run.title))
        # showing the results that we can tick
        self.assertContains(response, "0 of 1 selected")

    def test_admin_enrollment_changelist_search_by_course_title(self):
        """
        When we search with a course title, we should be able to find the enrollment
        that matches the user and the course title.
        """
        enrollment_search_url = reverse("admin:core_enrollment_changelist")
        search_parameters = {
            "q": self.course_run.course.title,
            "user__pk__exact": str(self.user.id),
        }

        response = self.client.get(enrollment_search_url, search_parameters)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed("admin/core/enrollment/change_list.html")
        self.assertContains(response, str(self.enrollment.user))
        self.assertContains(response, str(self.course_run.title))
        # showing the results that we can tick
        self.assertContains(response, "0 of 1 selected")

    def test_admin_enrollment_changelist_search_by_user_username(self):
        """
        When we search with a user's username, we should be able to find the enrollment
        that matches the user and his username.
        """
        enrollment_search_url = reverse("admin:core_enrollment_changelist")
        search_parameters = {
            "q": self.user.username,
            "user__pk__exact": str(self.user.id),
        }

        response = self.client.get(enrollment_search_url, search_parameters)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed("admin/core/enrollment/change_list.html")
        self.assertContains(response, str(self.enrollment.user))
        self.assertContains(response, str(self.course_run.title))
        # showing the results that we can tick
        self.assertContains(response, "0 of 1 selected")

    def test_admin_enrollment_changelist_search_by_user_email(self):
        """
        When we search with a user email, we should be able to find the enrollment
        that matches the user and his email.
        """
        enrollment_search_url = reverse("admin:core_enrollment_changelist")
        search_parameters = {
            "q": self.user.email,
            "user__pk__exact": str(self.user.id),
        }

        response = self.client.get(enrollment_search_url, search_parameters)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed("admin/core/enrollment/change_list.html")
        self.assertContains(response, str(self.enrollment.user))
        self.assertContains(response, str(self.course_run.title))
        # showing the results that we can tick
        self.assertContains(response, "0 of 1 selected")
