"""
Test suite for OfferingDeepLink update Admin API.
"""
from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class OfferingDeepLinkUpdateAdminApiTestCase(BaseAPITestCase):
    """Test suite for OfferingDeepLink update Admin API."""

    def test_admin_api_offering_deeplink_update_anonymous(self):
        """Anonymous user should not be able to update the deeplink of an offering"""
        deeplink = factories.OfferingDeepLinkFactory()
        offering = deeplink.offering

        response = self.client.put(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
            data={
                "deep_link": "https://www.deep-link-test-1.acme",
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_admin_api_offering_deeplink_update_with_lambda_user(self):
        """Authenticated lambda user should not be able to update the deeplink of an offering"""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        deeplink = factories.OfferingDeepLinkFactory()
        offering = deeplink.offering

        response = self.client.put(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
            data={
                "deep_link": "https://www.deep-link-test-1.acme",
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_admin_api_offering_deeplink_update_with_staff_user(self):
        """Authenticated lambda user should be able to update the deeplinks of an offering"""
        staff = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=staff.username, password="password")

        deeplink = factories.OfferingDeepLinkFactory(
            deep_link="https://test-deeplink-0.acme/"
        )
        offering = deeplink.offering

        response = self.client.put(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
            data={
                "deep_link": "https://www.deep-link-test-1.acme",
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_admin_api_offering_deeplink_update_superuser(self):
        """Authenticated admin superuser can update deeplink of an offering"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        [organization_1, organization_2] = factories.OrganizationFactory.create_batch(2)
        offering = factories.OfferingFactory(organizations=[organization_1, organization_2])
        offering_deeplink = factories.OfferingDeepLinkFactory(
            offering=offering,
            organization=organization_1,
            deep_link="https://test-deeplink-2.acme/",
        )

        response = self.client.put(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{offering_deeplink.id}/",
            data={
                "organization": str(organization_2.id),
                "deep_link": "https://test-deeplink-123.acme/"
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "id": str(offering_deeplink.id),
                "is_active": True,
                "deep_link": "https://test-deeplink-123.acme/",
                "offering": str(offering.id),
                "organization": str(organization_2.id),
            },
            response.json(),
        )

    def test_admin_api_offering_deeplink_partial_update_superuser(self):
        """Authenticated admin superuser can partially update deeplink of an offering"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        offering_deeplink = factories.OfferingDeepLinkFactory()
        organization = offering_deeplink.organization
        offering = offering_deeplink.offering

        response = self.client.put(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{offering_deeplink.id}/",
            data={
                "deep_link": "https://test-deeplink-456.acme/",
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "id": str(offering_deeplink.id),
                "is_active": True,
                "deep_link": "https://test-deeplink-456.acme/",
                "offering": str(offering.id),
                "organization": str(organization.id),
            },
            response.json(),
        )