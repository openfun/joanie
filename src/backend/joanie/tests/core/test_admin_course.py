"""
Test suite for courses admin pages
"""

from django.conf import settings
from django.urls import reverse

import lxml.html

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class CourseAdminTestCase(BaseAPITestCase):
    """Test suite for admin to manipulate courses."""

    def test_admin_course_use_translatable_change_form_with_actions_template(self):
        """
        The course admin change view should use a custom change form template
        to display both translation tabs of django parler and action buttons of
        django object actions.
        """
        # Create a course
        course = factories.CourseFactory()

        # Login a user with all permission to manage courses in django admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # Now we go to the course admin change view
        with self.assertTemplateUsed(
            "joanie/admin/translatable_change_form_with_actions.html"
        ):
            response = self.client.get(
                reverse("admin:core_course_change", args=(course.pk,)),
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, course.title)

        html = lxml.html.fromstring(response.content)

        # Django parler tabs should be displayed
        parler_tabs = html.cssselect(".parler-language-tabs span")
        self.assertEqual(len(parler_tabs), len(settings.LANGUAGES))

        # Django object actions should be displayed
        object_actions = html.cssselect(".objectaction-item")
        self.assertEqual(len(object_actions), 1)
        self.assertEqual(
            object_actions[0].attrib["data-tool-name"], "generate_certificates"
        )
