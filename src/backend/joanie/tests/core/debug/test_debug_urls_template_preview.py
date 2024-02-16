"""
Test suite for Debug app urls to preview templates (certificate, degree, invoice and
contract definition).

To test different DEBUG configurations from settings, we had to create two different test classes
to ensure that the routes were updated when executing a specific test.
If we don't create two distinct classes, the reload of urls configuration were not reflecting the
DEBUG setting value, and some routes were available when they should not be.
"""
from http import HTTPStatus

from django.core.cache import cache
from django.test import TestCase
from django.test.utils import override_settings

from joanie.tests.testing_utils import reload_urlconf


@override_settings(DEBUG=True)
class DebugEnabledUrlsTemplatePreviewTestCase(TestCase):
    """
    Test case for debug urls routes to preview template
    (certificate, degree, invoice and contract definition) when DEBUG is enabled.
    """

    def setUp(self):
        super().setUp()
        # Reset the cache to always reach the site route.
        cache.clear()
        # Force URLs reload to take DEBUG into account
        reload_urlconf()

    def test_debug_urls_template_preview_certificate_when_debug_is_true(
        self,
    ):
        """
        When `DEBUG` is set to `True`, the developer can access the view of the certificate
        to preview the template
        """
        response = self.client.get(path="/__debug__/pdf-templates/certificate")

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_debug_urls_template_preview_degree_when_debug_is_true(
        self,
    ):
        """
        When `DEBUG` is set to `True`, the developer can access the view of the degree
        to preview the template.
        """
        response = self.client.get(path="/__debug__/pdf-templates/degree")

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_debug_urls_template_preview_invoice_when_debug_is_true(
        self,
    ):
        """
        When `DEBUG` is set to `True`, the developer can access the view of an invoice
        to preview the template
        """
        response = self.client.get(path="/__debug__/pdf-templates/invoice")

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_debug_urls_template_preview_contract_definition_when_debug_is_true(
        self,
    ):
        """
        When `DEBUG` is set to `True`, the developer can access the view of the contract
        definition to preview the template.
        """
        response = self.client.get(path="/__debug__/pdf-templates/contract")

        self.assertEqual(response.status_code, HTTPStatus.OK)


@override_settings(DEBUG=False)
class DebugDisabledUrlsTemplatePreviewTestCase(TestCase):
    """
    Test case for debug urls routes to preview template
    (certificate, degree, invoice and contract definition) when DEBUG is disabled.
    """

    def setUp(self):
        super().setUp()
        # Reset the cache to always reach the site route.
        cache.clear()
        # Force URLs reload to take DEBUG into account
        reload_urlconf()

    def test_debug_urls_template_preview_certificate_when_debug_is_false(self):
        """
        When `DEBUG` is set to `False`, a user cannot access the view of the certificate
        to preview the template because urlpattern does not exist.
        """
        response = self.client.get(path="/__debug__/pdf-templates/certificate")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_debug_urls_template_preview_degree_when_debug_is_false(self):
        """
        When `DEBUG` is set to `False`, a user cannot access the view of the degree
        to preview the template because urlpattern does not exist.
        """
        response = self.client.get(path="/__debug__/pdf-templates/degree")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_debug_urls_template_preview_invoice_when_debug_is_false(self):
        """
        When `DEBUG` is set to `False`, a user cannot access the view of the invoice
        to preview the template because urlpattern does not exist.
        """
        response = self.client.get(path="/__debug__/pdf-templates/invoice")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_debug_urls_template_preview_contract_definition_when_debug_is_false(
        self,
    ):
        """
        When `DEBUG` is set to `False`, a user cannot access the view of the contract
        definition to preview the template because urlpattern does not exist.
        """
        response = self.client.get(path="/__debug__/pdf-templates/contract")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
