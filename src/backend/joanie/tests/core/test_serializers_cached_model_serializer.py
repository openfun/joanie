"""Tests for the CachedModelSerializer class."""

from django.test import TestCase, override_settings

from rest_framework import serializers

from joanie.core import factories, models
from joanie.core.serializers.base import CachedModelSerializer


class TestCachedModelSerializer(TestCase):
    """Test suite for the CachedModelSerializer class."""

    def test_serializers_cached_model_serializer_cache_representation(self):
        """
        The CachedModelSerializer should return a cached representation of the
        resource until the resource has been updated.
        """

        class AddressCachedSerializer(CachedModelSerializer):
            """A Test Serializer based on Address Model."""

            class Meta:
                model = models.Address
                fields = ("title",)

        # - First serializer should return address title and is_main property
        address = factories.UserAddressFactory(title="Home")
        serializer = AddressCachedSerializer(address)
        self.assertEqual(serializer.data, {"title": "Home"})

        # - Then even if the address resource is updated, the serializer should return
        # its cached value
        address.title = "Work"
        serializer = AddressCachedSerializer(address)
        self.assertEqual(serializer.data, {"title": "Home"})

        # - But once the resource is saved, its cached key should have been updated
        #   so the serializer should return an up-to-date value
        address.save()
        serializer = AddressCachedSerializer(address)
        self.assertEqual(serializer.data, {"title": "Work"})

    def test_serializers_cached_model_multiple_serializer_cache_representation(self):
        """
        The CachedModelSerializer should return a cached representation of the
        resource until the resource has been updated.
        """
        CachedAddress = models.Address
        CachedAddress.cached_serializers = [
            "AddressCachedSerializer",
            "OtherAddressCachedSerializer",
        ]

        class AddressCachedSerializer(CachedModelSerializer):
            """A Test Serializer based on Address Model."""

            owner = serializers.SerializerMethodField(read_only=True)

            class Meta:
                model = models.Address
                fields = ("title", "owner")

            def get_owner(self, obj):
                """Return the owner username."""
                return obj.owner.username

        class OtherAddressCachedSerializer(CachedModelSerializer):
            """A Test Serializer based on Address Model."""

            owner = serializers.SerializerMethodField(read_only=True)

            class Meta:
                model = models.Address
                fields = ("title", "address", "owner")

            def get_owner(self, obj):
                """Return the owner username."""
                return obj.owner.username

        # - First serializer should return address title
        owner = factories.UserFactory(username="owner")
        address = factories.UserAddressFactory(
            title="Home", address="1 Home Street", owner=owner
        )
        serializer = AddressCachedSerializer(address)
        self.assertEqual(serializer.data, {"title": "Home", "owner": "owner"})

        # - Second serializer should return address title and address
        serializer = OtherAddressCachedSerializer(address)
        self.assertEqual(
            serializer.data,
            {"title": "Home", "address": "1 Home Street", "owner": "owner"},
        )

        # - Then even if the owner resource is updated, the serializers should return
        #   their cached value
        owner.username = "new_username"
        serializer = AddressCachedSerializer(address)
        self.assertEqual(serializer.data, {"title": "Home", "owner": "owner"})
        serializer = OtherAddressCachedSerializer(address)
        self.assertEqual(
            serializer.data,
            {"title": "Home", "address": "1 Home Street", "owner": "owner"},
        )

        # - But once the resource cache is cleared,
        #   its cached key should have been updated
        #   so the serializers should return up-to-date values
        address.clear_cache()
        serializer = AddressCachedSerializer(address)
        self.assertEqual(serializer.data, {"title": "Home", "owner": "new_username"})
        serializer = OtherAddressCachedSerializer(address)
        self.assertEqual(
            serializer.data,
            {"title": "Home", "address": "1 Home Street", "owner": "new_username"},
        )

    @override_settings(JOANIE_SERIALIZER_DEFAULT_CACHE_TTL=0)
    def test_serializers_cached_model_serializer_cache_representation_cache_ttl_global_settings(
        self,
    ):
        """
        The CachedModelSerializer should use
        JOANIE_ANONYMOUS_SERIALIZER_DEFAULT_CACHE_TTL setting as default value.
        """

        class AddressCachedSerializer(CachedModelSerializer):
            """A Test Serializer based on Address Model."""

            class Meta:
                model = models.Address
                fields = ("title",)

        # - First serializer should return address title and is_main property
        address = factories.UserAddressFactory(title="Home")
        serializer = AddressCachedSerializer(address)
        self.assertEqual(serializer.data, {"title": "Home"})

        # - As JOANIE_ANONYMOUS_SERIALIZER_DEFAULT_CACHE_TTL is equal to 0, the cache
        # should be stale immediately, so the serializer should return
        # an up-to-date value
        address.title = "Work"
        serializer = AddressCachedSerializer(address)
        self.assertEqual(serializer.data, {"title": "Work"})

    def test_serializers_cached_model_serializer_cache_representation_with_custom_cache_ttl(
        self,
    ):
        """
        The CachedModelSerializer should allow to customize the cache lifetime.
        """

        class AddressCachedSerializer(CachedModelSerializer):
            """A Test Serializer based on Address Model."""

            class Meta:
                cache_ttl = 0
                model = models.Address
                fields = ("title",)

        # - First serializer should return address title and is_main property
        address = factories.UserAddressFactory(title="Home")
        serializer = AddressCachedSerializer(address)
        self.assertEqual(serializer.data, {"title": "Home"})

        # - As cache_ttl is equal to 0, the cache should be stale immediately, so
        #   the serializer should return an up-to-date value
        address.title = "Work"
        serializer = AddressCachedSerializer(address)
        self.assertEqual(serializer.data, {"title": "Work"})
