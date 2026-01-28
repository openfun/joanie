"""
Test suite for OfferingDeepLink list Admin API.
"""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class OfferingDeepLinkListAdminApiTestCase(BaseAPITestCase):
    """Test suite for OfferingDeepLink list Admin API."""

    def test_admin_api_offering_deeplink_list_anonymous(self):
        """Anonymous user should not be able to list deeplinks of an offering."""
        offering = factories.OfferingFactory()

        response = self.client.get(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_admin_api_offering_deeplink_list_with_lambda_user(self):
        """Authenticated lambda user should not be able to list deeplinks of an offering."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        offering = factories.OfferingFactory()

        response = self.client.get(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_admin_api_offering_deeplink_list_with_staff_user(self):
        """Staff user with basic permissions should be able to list deeplinks of an offering."""
        staff = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=staff.username, password="password")

        [organization_1, organization_2] = factories.OrganizationFactory.create_batch(2)
        offering = factories.OfferingFactory(
            organizations=[organization_1, organization_2]
        )
        deeplink_ids = []
        for i, organization in enumerate([organization_1, organization_2]):
            deeplink_id = factories.OfferingDeepLinkFactory(
                offering=offering,
                organization=organization,
                deep_link=f"https://test-deeplink-{i}.acme/",
            ).id
            deeplink_ids.append(deeplink_id)

        response = self.client.get(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(deeplink_ids[1]),
                        "is_active": True,
                        "deep_link": "https://test-deeplink-1.acme/",
                        "offering": str(offering.id),
                        "organization": str(organization_2.id),
                    },
                    {
                        "id": str(deeplink_ids[0]),
                        "is_active": True,
                        "deep_link": "https://test-deeplink-0.acme/",
                        "offering": str(offering.id),
                        "organization": str(organization_1.id),
                    },
                ],
            },
            response.json(),
        )

    def test_admin_api_offering_deeplink_list_authenticated_superuser(self):
        """Authenticated admin superuser can list deeplinks of an offering."""
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
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(deeplink.id),
                        "is_active": True,
                        "deep_link": "https://test-deeplink-2.acme/",
                        "offering": str(offering.id),
                        "organization": str(organization.id),
                    },
                ],
            },
            response.json(),
        )
