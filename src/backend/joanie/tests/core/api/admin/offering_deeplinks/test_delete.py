"""
Test suite for OfferingDeepLink delete Admin API.
"""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class OfferingDeepLinkDeleteAdminApiTestCase(BaseAPITestCase):
    """
    Test suite for OfferingDeepLink delete Admin API.
    """

    def test_admin_api_offering_deeplink_delete_anonymous(self):
        """Anonymous user should not be able to delete an offering deep link."""
        deeplink = factories.OfferingDeepLinkFactory()
        offering = deeplink.offering

        response = self.client.delete(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_admin_api_offering_deeplink_delete_staff(self):
        """Staff user with basic permissions should not be able to delete an offering deep link."""
        staff = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=staff.username, password="password")
        deeplink = factories.OfferingDeepLinkFactory()
        offering = deeplink.offering

        response = self.client.delete(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_admin_api_offering_deeplink_delete_lambda(self):
        """Lambda authenticated user should not be able to delete an offering deep link."""
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")
        deeplink = factories.OfferingDeepLinkFactory()
        offering = deeplink.offering

        response = self.client.delete(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_admin_api_offering_deeplink_delete_authenticated_superuser(self):
        """
        Authenticated admin user should be able to delete an offering deep link
        if it's not active.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        deeplink = factories.OfferingDeepLinkFactory(is_active=True)
        offering = deeplink.offering

        response = self.client.delete(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            ["You cannot delete this offering deep link, it's active."], response.json()
        )

        deeplink.is_active = False
        deeplink.save()

        response = self.client.delete(
            f"/api/v1.0/admin/offerings/{offering.id}/offering-deeplinks/{deeplink.id}/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NO_CONTENT)
