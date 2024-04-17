# ruff: noqa: PLR0912
# pylint: disable=too-many-branches
"""Test suite for the sentry utils."""

from unittest import mock

from django.core.serializers.json import DjangoJSONEncoder
from django.test import TestCase, override_settings

from factory.base import FactoryMetaClass

from joanie.badges import factories as badges_factories
from joanie.core import factories as core_factories
from joanie.core.enums import PAYMENT_STATE_PENDING
from joanie.core.utils.sentry import (
    before_send,
    decrypt_data,
    encrypt_data,
    encrypt_extra,
)
from joanie.payment import factories as payment_factories

factories = []
factories.extend(core_factories.__dict__.values())
factories.extend(payment_factories.__dict__.values())
factories.extend(badges_factories.__dict__.values())


@override_settings(LOGGING_SECRET_KEY="9Jg_wqPAr1LF6JCA3iVX6v8lW3fixjW85d0QVsIqXcw=")
class UtilsSentryTestCase(TestCase):
    """Test the sentry utils"""

    maxDiff = None

    def test_encrypt_data(self):
        """
        Test the encryption of data

        We test the encryption of data and then decrypt it to check if the data is the same
        All the factories are tested
        """
        for factory in factories:
            if isinstance(factory, FactoryMetaClass):
                # AddressFactory needs an owner or an organization
                if "<AddressFactory" in str(factory):
                    obj = factory(owner=core_factories.UserFactory())
                else:
                    obj = factory()

                # Our models have a to_dict method to serialize them
                if hasattr(obj, "to_dict"):
                    encrypted_data = encrypt_data(obj.to_dict())
                # but others don't
                else:
                    encrypted_data = encrypt_data(obj)

                decrypted_data = decrypt_data(encrypted_data)
                if hasattr(obj, "to_dict"):
                    for key, value in obj.to_dict().items():
                        try:
                            self.assertEqual(decrypted_data[key], value)
                        except AssertionError:
                            if value is None:
                                self.assertIsNone(decrypted_data[key])
                            else:
                                self.assertIsNotNone(decrypted_data[key])
                else:
                    if obj.__class__.__name__ == "Site":
                        self.assertEqual(decrypted_data, obj.domain)
                        continue
                    self.assertEqual(decrypted_data, obj)

    def test_encrypt_organization(self):
        """
        Test the encryption of an organization

        Specific test for ImageFieldFile, ThumbnailerImageFieldFile and Country
        """
        organization = core_factories.OrganizationFactory()

        encrypted_data = encrypt_data(organization.to_dict())

        decrypted_data = decrypt_data(encrypted_data)
        self.assertEqual(decrypted_data["signature"], organization.signature.path)
        self.assertEqual(decrypted_data["logo"], organization.logo.path)
        self.assertEqual(decrypted_data["country"], organization.country.name)

    def test_encrypt_site(self):
        """
        Test the encryption of a site

        Specific test for Site
        """
        site = core_factories.SiteFactory()

        encrypted_data = encrypt_data(site)

        decrypted_data = decrypt_data(encrypted_data)
        self.assertEqual(decrypted_data, site.domain)

    @mock.patch("joanie.core.utils.sentry.SentryEncoder")
    def test_encrypt_organization_fail(self, mock_sentry_encoder):
        """
        If serialization fails, return the data as is, unencrypted
        """
        mock_sentry_encoder.side_effect = DjangoJSONEncoder
        organization = core_factories.OrganizationFactory()

        encrypted_data = encrypt_data(organization.to_dict())

        self.assertEqual(encrypted_data, organization.to_dict())

    def test_encrypt_order_payment_schedule(self):
        """
        Test the encryption of an order payment schedule
        """
        order = core_factories.OrderFactory(
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
            ]
        )

        encrypted_data = encrypt_data(order.to_dict())

        decrypted_data = decrypt_data(encrypted_data)
        self.assertEqual(decrypted_data["payment_schedule"][0]["amount"], "200.00")
        self.assertEqual(decrypted_data["payment_schedule"][1]["amount"], "300.00")

    def test_encrypt_extra(self):
        """
        Test the encryption of extra data

        We test the encryption of extra data and then decrypt it to check if the data is the same.
        """
        encrypted_data = encrypt_extra(
            {
                "application": "backend",
                "sys.argv": ["test", "-c"],
                "context": {"test": "test"},
                "payload": {
                    "test": "test",
                    "test2": "test",
                    "test3": "test",
                },
            }
        )

        self.assertEqual(encrypted_data["application"], "backend")
        self.assertEqual(encrypted_data["sys.argv"], ["test", "-c"])

        decrypted_data = decrypt_data(encrypted_data.get("encrypted_context"))

        self.assertEqual(
            decrypted_data,
            {
                "context": {"test": "test"},
                "payload": {
                    "test": "test",
                    "test2": "test",
                    "test3": "test",
                },
            },
        )

    @override_settings(LOGGING_SECRET_KEY=None)
    def test_encrypt_extra_no_logging_secret_key(self):
        """
        Test the encryption of extra data

        We test the encryption of extra data and then decrypt it to check if the data is the same.
        """
        encrypted_data = encrypt_extra(
            {
                "application": "backend",
                "sys.argv": ["test", "-c"],
                "context": {"test": "test"},
                "payload": {
                    "test": "test",
                    "test2": "test",
                    "test3": "test",
                },
            }
        )

        self.assertEqual(
            encrypted_data,
            {
                "application": "backend",
                "sys.argv": ["test", "-c"],
                "context": {"test": "test"},
                "payload": {
                    "test": "test",
                    "test2": "test",
                    "test3": "test",
                },
            },
        )

    def test_encrypt_extra_empty(self):
        """
        Test the encryption of extra data

        We test the encryption of extra data and then decrypt it to check if the data is the same.
        """
        encrypted_data = encrypt_extra(
            {
                "application": "backend",
                "sys.argv": ["test", "-c"],
            }
        )

        self.assertEqual(encrypted_data["application"], "backend")
        self.assertEqual(encrypted_data["sys.argv"], ["test", "-c"])
        self.assertIsNone(encrypted_data.get("encrypted_context"))

    def test_before_send(self):
        """
        Test the before_send function

        Extra data and breadcrumbs are encrypted.
        """
        event = {
            "extra": {
                "application": "backend",
                "sys.argv": ["test", "-c"],
                "context": {"test": "test"},
                "payload": {
                    "test": "test",
                    "test2": "test",
                    "test3": "test",
                },
            },
            "breadcrumbs": {
                "values": [
                    {
                        "data": {
                            "application": "backend",
                            "sys.argv": ["test", "-c"],
                            "context": {"test": "test"},
                            "payload": {
                                "test": "test",
                                "test2": "test",
                                "test3": "test",
                            },
                        }
                    }
                ]
            },
        }

        encrypted_event = before_send(event, None)
        extra = encrypted_event["extra"]
        breadcrumb_data = encrypted_event["breadcrumbs"]["values"][0]["data"]

        self.assertEqual(extra["application"], "backend")
        self.assertEqual(extra["sys.argv"], ["test", "-c"])
        self.assertEqual(breadcrumb_data["application"], "backend")
        self.assertEqual(breadcrumb_data["sys.argv"], ["test", "-c"])

        decrypted_extra = decrypt_data(extra.get("encrypted_context"))
        self.assertEqual(
            decrypted_extra,
            {
                "context": {"test": "test"},
                "payload": {
                    "test": "test",
                    "test2": "test",
                    "test3": "test",
                },
            },
        )

        decrypted_breadcrumb_data = decrypt_data(
            breadcrumb_data.get("encrypted_context")
        )
        self.assertEqual(
            decrypted_breadcrumb_data,
            {
                "context": {"test": "test"},
                "payload": {
                    "test": "test",
                    "test2": "test",
                    "test3": "test",
                },
            },
        )
