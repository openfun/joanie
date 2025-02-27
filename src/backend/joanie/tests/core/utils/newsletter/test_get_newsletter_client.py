"""Test suite for get_newsletter_client"""

from unittest.mock import patch

from django.test import TestCase, override_settings

from joanie.core.utils.newsletter import get_newsletter_client


class GetNewsletterClientTestCase(TestCase):
    """Test suite for the get_newsletter_client function."""

    @override_settings(JOANIE_NEWSLETTER_CLIENT=None)
    def test_get_newsletter_client_with_no_client_configured(self):
        """
        When no newsletter client is configured in settings,
        the function should return None.
        """
        client = get_newsletter_client()
        self.assertIsNone(client)

    @override_settings(JOANIE_NEWSLETTER_CLIENT="path.to.dummy.NewsletterClient")
    @patch("joanie.core.utils.newsletter.import_string")
    def test_get_newsletter_client_with_client_configured(self, mock_import_string):
        """
        When a newsletter client is configured in settings,
        the function should import and return the client class.
        """
        # Setup mock
        mock_client_class = type("DummyNewsletterClient", (), {})
        mock_import_string.return_value = mock_client_class

        # Call the function
        client = get_newsletter_client()

        # Assertions
        mock_import_string.assert_called_once_with("path.to.dummy.NewsletterClient")
        self.assertEqual(client, mock_client_class)

    @override_settings(JOANIE_NEWSLETTER_CLIENT="path.to.invalid.NewsletterClient")
    def test_get_newsletter_client_raise_importerror(self):
        """
        When JOANIE_NEWSLETTER_CLIENT is invalid an ImportError should be raised.
        """
        with self.assertRaises(ImportError):
            get_newsletter_client()
