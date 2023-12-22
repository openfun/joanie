"""
Tests for Organization web hook.
"""
import base64
from os.path import dirname, join, realpath
from unittest import mock

from django.core.files.storage import default_storage
from django.test import TestCase, override_settings

from joanie.core.models import Organization
from joanie.lms_handler import api

LOGO_NAME = "creative_common.jpeg"
with open(join(dirname(realpath(__file__)), f"images/{LOGO_NAME}"), "rb") as logo:
    LOGO_BASE64 = str(base64.b64encode(logo.read()))


@override_settings(
    JOANIE_SYNC_SECRETS=["shared secret"],
    JOANIE_LMS_BACKENDS=[
        {
            "BASE_URL": "http://localhost:8073",
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "ORGANIZATION_REGEX": r"^.*/organizations/(?P<organization_id>.*)/organization/?$",
            "JS_BACKEND": "base",
            "JS_ORGANIZATION_REGEX": r"^.*/organizations/(?<organization_id>.*)/organization/?$",
        }
    ],
    TIME_ZONE="UTC",
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
    },
)
class SyncOrganizationApiTestCase(TestCase):
    """Test calls to sync an organization via API endpoint."""

    def tearDown(self):
        default_storage.delete(LOGO_NAME)

    def test_api_organizations_sync_missing_signature(self):
        """The organization run synchronization API endpoint requires a signature."""
        data = {
            "code": "ORGA",
            "title": "Organization 1",
            "logo": LOGO_BASE64,
        }

        response = self.client.post(
            "/api/v1.0/organizations-sync", data, content_type="application/json"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "Missing authentication."})
        self.assertEqual(Organization.objects.count(), 0)

    def test_api_organizations_sync_invalid_signature(self):
        """The organization run synchronization API endpoint requires a valid signature."""
        data = {
            "code": "ORGA",
            "title": "Organization 1",
            "logo": LOGO_BASE64,
        }

        response = self.client.post(
            "/api/v1.0/organizations-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION="invalid authorization",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid authentication."})
        self.assertEqual(Organization.objects.count(), 0)

    def test_api_organizations_sync_valid_signature(self):
        """
        If signature is valid, it should return a 200 response.
        """
        data = {
            "code": "ORGA",
            "title": "Organization 1",
        }

        response = self.client.post(
            "/api/v1.0/organizations-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                "SIG-HMAC-SHA256 42927bc9650a07c75a3b5c1dc2f9e8f14216d8085ae45bb43fd2a76fc25e5504"
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})

    def test_api_organizations_sync_missing_code(self):
        """
        If the data submitted is missing a code, it should return a 400 error.
        """
        data = {
            "name": "Organization 1",
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/organizations-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"code": ["This field is required."]})
        self.assertEqual(Organization.objects.count(), 0)

    def test_api_organizations_sync_create(self):
        """
        If the data submitted is valid, it should create a new organization.
        """
        data = {
            "code": "ORGA",
            "title": "Organization 1",
            "logo_base64": LOGO_BASE64,
            "logo_name": LOGO_NAME,
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/organizations-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(Organization.objects.count(), 1)
        organization = Organization.objects.first()
        self.assertEqual(organization.code, "ORGA")
        self.assertEqual(organization.title, "Organization 1")
        self.assertEqual(organization.logo.name, LOGO_NAME)
        self.assertIsNotNone(organization.logo.read())
        self.assertTrue(default_storage.exists(organization.logo.name))

    def test_api_organizations_sync_update(self):
        """
        If the data submitted is valid, it should update an existing organization.
        """
        Organization.objects.create(
            code="orga",
            title="Organization 1 old title",
            logo=None,
        )

        data = {
            "code": "ORGA",
            "title": "Organization 1",
            "logo_base64": LOGO_BASE64,
            "logo_name": LOGO_NAME,
        }

        with mock.patch.object(api, "authorize_request") as mock_authorize_request:
            mock_authorize_request.return_value = None
            response = self.client.post(
                "/api/v1.0/organizations-sync",
                data,
                content_type="application/json",
                HTTP_AUTHORIZATION="SIG-HMAC-SHA256 mocked signature",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(Organization.objects.count(), 1)
        organization = Organization.objects.first()
        self.assertEqual(organization.code, "ORGA")
        self.assertEqual(organization.title, "Organization 1")
        self.assertEqual(organization.logo.name, LOGO_NAME)
        self.assertIsNotNone(organization.logo.read())
        self.assertTrue(default_storage.exists(organization.logo.name))
