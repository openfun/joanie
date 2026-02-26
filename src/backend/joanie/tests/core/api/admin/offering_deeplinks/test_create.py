"""
Test suite for OfferingDeepLink create Admin API.
"""

from http import HTTPStatus

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class OfferingDeepLinkCreateAdminApiTestCase(BaseAPITestCase):
    """
    Test suite for OfferingDeepLink create Admin API.
    """

    maxDiff = None

    def test_admin_api_create_offering_deeplink_anonymous(self):
        """Anonymous user should not be able to create a deep link for an offering."""
        offering = factories.OfferingFactory()
        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
            data={
                "organization_id": str(organization.id),
                "deep_link": "https//test-deeplink-1.com/",
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_admin_api_create_offering_deeplink_with_lambda_user(self):
        """
        Lambda user should not be able to create a deep link on an offering for an organization.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory()
        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
            data={
                "organization_id": str(organization.id),
                "deep_link": "https//test-deeplink-2.com/",
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_admin_api_create_offering_deeplink_staff_user(self):
        """
        Staff user with basic permissions should not be able to create a deep link
        of an offering for organizations.
        """
        staff = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=staff.username, password="password")
        offering = factories.OfferingFactory()
        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
            data={
                "organization_id": str(organization.id),
                "deep_link": "https//test-deeplink-2.com/",
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_admin_api_create_one_deeplink_per_organization_and_per_offering(self):
        """
        Admin authenticated user should not be able to create two deeplinks for the same
        offering and organization.
        """
        staff = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=staff.username, password="password")
        organization = factories.OrganizationFactory()
        offering = factories.OfferingFactory(organizations=[organization])
        factories.OfferingDeepLinkFactory(organization=organization, offering=offering)

        response = self.client.post(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
            data={
                "organization_id": str(organization.id),
                "deep_link": "https//test-deeplink-3.com/",
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_admin_api_create_offering_deeplink_missing_organization(self):
        """
        Admin user should not be able to create a deep link with missing organization value.
        """
        staff = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=staff.username, password="password")
        offering = factories.OfferingFactory()

        response = self.client.post(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
            data={
                "deep_link": "https//test-deeplink-4.com/",
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_admin_api_create_offering_deeplink_missing_offering(self):
        """
        Admin user should not be able to create a deep link with missing offering value.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory()
        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
            data={
                "organization_id": str(organization.id),
                "deep_link": "https//test-deeplink-4.com/",
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_admin_api_create_offering_deeplink_missing_deep_link(self):
        """
        Authenticated admin user should not be able to create a deep link with missing deep
        link value.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory()
        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
            data={
                "organization_id": str(organization.id),
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_admin_api_create_offering_deeplink_organization_not_related_to_offering(
        self,
    ):
        """
        Authenticated admin user should not be able to create a deeplink for an organization
        that is not related to the offering. We should get an error in return.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        offering = factories.OfferingFactory()

        response = self.client.post(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
            data={
                "organization_id": str(organization.id),
                "deep_link": "https://test-deeplink-5.com/",
            },
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_admin_api_create_offering_deeplink_authenticated_superuser(self):
        """
        Authenticated admin user should be to create a deep link of an offering
        for an organization.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        offering = factories.OfferingFactory(organizations=[organization])

        response = self.client.post(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/",
            data={
                "organization_id": str(organization.id),
                "deep_link": "https://test-deeplink-6.com/",
            },
            content_type="application/json",
        )

        deeplink = models.OfferingDeepLink.objects.get()

        self.assertStatusCodeEqual(response, HTTPStatus.CREATED)
        self.assertDictEqual(
            {
                "id": str(deeplink.id),
                "deep_link": "https://test-deeplink-6.com/",
                "is_active": False,
                "offering": str(offering.id),
                "organization": str(organization.id),
            },
            response.json(),
        )
