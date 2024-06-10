"""Test suite for the SiteConfig model."""

from django.test import TestCase

from joanie.core.factories import SiteConfigFactory


class SiteConfigModelTestSuite(TestCase):
    """Test suite for the SiteConfig model."""

    def test_models_site_config(self):
        """Test the SiteConfig model."""
        site = SiteConfigFactory(site__name="Joanie site")
        self.assertEqual(str(site), "Site config for Joanie site")

    def test_models_site_config_get_terms_and_conditions_in_html(self):
        """
        Test the get_terms_and_conditions_in_html method.
        It should return the terms and conditions in html format in the current language
        if it exists.
        """
        site_config = SiteConfigFactory()

        with self.assertRaises(DeprecationWarning) as deprecation_warning:
            site_config.get_terms_and_conditions_in_html()

        self.assertEqual(
            str(deprecation_warning.exception),
            "Terms and conditions are managed through contract definition body.",
        )
