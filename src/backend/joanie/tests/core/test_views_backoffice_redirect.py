"""BackOfficeRedirectView test suite."""

from django.test import TestCase, override_settings
from django.urls import reverse


class BackofficeRedirectViewTestCase(TestCase):
    """
    The BackOfficeRedirectView test suite.
    """

    @override_settings(JOANIE_BACKOFFICE_BASE_URL="https://bo.joanie.test")
    def test_views_redirects_backoffice(self):
        """
        BackOfficeRedirectView should redirect to the backoffice url according to the
        settings JOANIE_BACKOFFICE_BASE_URL and the path catched in the url.
        """
        url = reverse(
            "redirect-to-backoffice", kwargs={"path": "admin/core/organizations/"}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response["Location"],
            "https://bo.joanie.test/admin/core/organizations/",
        )
