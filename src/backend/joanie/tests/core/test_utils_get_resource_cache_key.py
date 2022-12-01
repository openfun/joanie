"""Util 'get_resource_cache_key' test suite"""
from unittest import TestCase

from django.test import override_settings

from joanie.core.utils import get_resource_cache_key


class GetResourceCacheKeyTestCase(TestCase):
    """Test suite for util `get_resource_cache_key`."""

    def test_utils_get_resource_cache_key(self):
        """Resource cache key insensitive to language."""
        cache_key = get_resource_cache_key("resource", 1)
        self.assertEqual(cache_key, "resource-1")

    @override_settings(LANGUAGE_CODE="de-de")
    def test_utils_get_resource_cache_key_language_sensitive(self):
        """Resource cache key can be sensitive to language."""
        cache_key = get_resource_cache_key("resource", 1, is_language_sensitive=True)
        self.assertEqual(cache_key, "resource-1-de-de")

    def test_utils_get_resource_cache_key_with_language(self):
        """Resource cache key binds a provided language."""
        cache_key = get_resource_cache_key("resource", 1, language="fr-fr")
        self.assertEqual(cache_key, "resource-1-fr-fr")

    def test_utils_get_resource_cache_key_language_sensitive_with_language(self):
        """Resource cache key binds the provided language even if is_language_sensitive is True."""
        cache_key = get_resource_cache_key(
            "resource", 1, is_language_sensitive=True, language="fr-fr"
        )
        self.assertEqual(cache_key, "resource-1-fr-fr")
