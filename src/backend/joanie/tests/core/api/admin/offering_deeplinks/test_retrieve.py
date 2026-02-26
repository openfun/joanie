"""
Test suite for OfferingDeepLink retrieve Admin API.
"""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class OfferingDeepLinkRetrieveAdminApiTestCase(BaseAPITestCase):
    """Test suite for OfferingDeepLink retrieve Admin API."""

    def test_admin_api_offering_deeplink_retrieve_anonymous(self):
        """Anonymous user should not be able to retrieve the deeplink of an offering."""
        deeplink = factories.OfferingDeepLinkFactory()
        offering = deeplink.offering

        response = self.client.get(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_admin_api_offering_deeplink_retrieve_with_lambda_user(self):
        """Authenticated lambda user should not be able to retrieve the deeplink of an offering."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        deeplink = factories.OfferingDeepLinkFactory()
        offering = deeplink.offering

        response = self.client.get(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_admin_api_offering_deeplink_retrieve_with_staff_user(self):
        """Staff user with basic permissions should be able to retrieve deeplink of an offering."""
        staff = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=staff.username, password="password")
        deeplink = factories.OfferingDeepLinkFactory(
            deep_link="https://test-deeplink-0.acme/"
        )
        offering = deeplink.offering
        organization = deeplink.organization

        response = self.client.get(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "id": str(deeplink.id),
                "is_active": True,
                "deep_link": "https://test-deeplink-0.acme/",
                "offering": str(offering.id),
                "organization": str(organization.id),
            },
            response.json(),
        )

    def test_admin_api_offering_deeplink_retrieve_authenticated_superuser(self):
        """Authenticated admin superuser can retrieve deeplink of an offering."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        offering = factories.OfferingFactory(organizations=[organization])
        deeplink = factories.OfferingDeepLinkFactory(
            offering=offering,
            organization=organization,
            deep_link="https://test-deeplink-2.acme/",
        )

        response = self.client.get(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "id": str(deeplink.id),
                "is_active": True,
                "deep_link": deeplink.deep_link,
                "offering": str(offering.id),
                "organization": str(organization.id),
            },
            response.json(),
        )
