"""Product model 'get_cache_key' test suite"""
from datetime import datetime
from unittest import mock

from django.test import TestCase, override_settings

from joanie.core import factories


class GetCacheKeyProductModelsTestCase(TestCase):
    """Test suite for `get_cache_key` method on the Product model."""

    def test_models_product_product_get_cache_key(self):
        """Product cache key should be insensitive to language by default."""
        mocked_now = datetime(2023, 9, 16, 12, 5, 3, 123456)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            product = factories.ProductFactory(
                id="67e3c639-7a00-4f0e-8a3f-159e59a0d351"
            )

        cache_key = product.get_cache_key("1")
        self.assertEqual(
            cache_key, "1-67e3c639-7a00-4f0e-8a3f-159e59a0d351-1694865903.123456"
        )

        # Updating the instance should change the cache key
        mocked_now = datetime(2023, 10, 12, 8, 8, 7, 456789)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            product.save()

        cache_key = product.get_cache_key("1")
        self.assertEqual(
            cache_key, "1-67e3c639-7a00-4f0e-8a3f-159e59a0d351-1697098087.456789"
        )

    @override_settings(LANGUAGE_CODE="de-de")
    def test_models_product_get_cache_key_language_sensitive(self):
        """Product cache key can be sensitive to language."""
        mocked_now = datetime(2023, 9, 16, 12, 5, 3, 123456)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            product = factories.ProductFactory(
                id="67e3c639-7a00-4f0e-8a3f-159e59a0d351"
            )

        cache_key = product.get_cache_key("1", is_language_sensitive=True)
        self.assertEqual(
            cache_key, "1-67e3c639-7a00-4f0e-8a3f-159e59a0d351-1694865903.123456-de-de"
        )

    def test_models_product_get_cache_key_with_language(self):
        """Product cache key binds a provided language."""
        mocked_now = datetime(2023, 9, 16, 12, 5, 3, 123456)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            product = factories.ProductFactory(
                id="67e3c639-7a00-4f0e-8a3f-159e59a0d351"
            )

        cache_key = product.get_cache_key("1", language="fr-fr")
        self.assertEqual(
            cache_key, "1-67e3c639-7a00-4f0e-8a3f-159e59a0d351-1694865903.123456-fr-fr"
        )

    def test_models_product_get_cache_key_language_sensitive_with_language(self):
        """Product cache key binds the provided language even if is_language_sensitive is True."""
        mocked_now = datetime(2023, 9, 16, 12, 5, 3, 123456)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            product = factories.ProductFactory(
                id="67e3c639-7a00-4f0e-8a3f-159e59a0d351"
            )

        cache_key = product.get_cache_key(
            "1", is_language_sensitive=True, language="fr-fr"
        )
        self.assertEqual(
            cache_key, "1-67e3c639-7a00-4f0e-8a3f-159e59a0d351-1694865903.123456-fr-fr"
        )
