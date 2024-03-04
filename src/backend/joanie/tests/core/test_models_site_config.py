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
        terms_markdown_english = """
        ## Terms and conditions
        Here are the terms and conditions of the current site.
        """

        terms_markdown_french = """
        ## Conditions générales de ventes
        Voici les conditions générales de ventes du site.
        """

        site_config = SiteConfigFactory()

        # If no translation exists, it should return an empty string
        self.assertEqual(site_config.get_terms_and_conditions_in_html(), "")

        # Create default language and french translations of the terms and conditions
        site_config.translations.create(terms_and_conditions=terms_markdown_english)
        site_config.translations.create(
            language_code="fr", terms_and_conditions=terms_markdown_french
        )

        # It should use the default language if no language is provided
        self.assertEqual(
            site_config.get_terms_and_conditions_in_html(),
            (
                "<h2>Terms and conditions</h2>\n"
                "<p>Here are the terms and conditions of the current site.</p>"
            ),
        )

        # It should use the provided language if it exists
        self.assertEqual(
            site_config.get_terms_and_conditions_in_html("fr"),
            (
                "<h2>Conditions générales de ventes</h2>\n"
                "<p>Voici les conditions générales de ventes du site.</p>"
            ),
        )

        # It should fallback to the default language if the provided language does not exist
        self.assertEqual(
            site_config.get_terms_and_conditions_in_html("de"),
            (
                "<h2>Terms and conditions</h2>\n"
                "<p>Here are the terms and conditions of the current site.</p>"
            ),
        )
