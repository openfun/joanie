"""Test suite for the admin OfferingViewSet to toggle deeplinks"""

from http import HTTPStatus

from joanie.core import enums, factories
from joanie.tests.base import BaseAPITestCase


class OfferingViewSetToggleDeepLinkTestCase(BaseAPITestCase):
    """Test suite for the admin OfferingViewSet to toggle deeplinks"""

    def test_admin_api_offering_toggle_deeplink_anonymous(self):
        """
        Anonymous user should not be able to toggle deep links of an offering.
        """
        offering = factories.OfferingFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/offerings/{offering.id}/toggle-deeplinks/",
            data={"is_active": True},
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_admin_api_offering_toggle_deeplink_lambda_user(self):
        """
        Lambda user should not be able to toggle deep links of an offering.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        offering = factories.OfferingFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/offerings/{offering.id}/toggle-deeplinks/",
            data={"is_active": True},
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_admin_api_offering_toggle_deeplink_staff_user(self):
        """
        Basic staff user with permissions should not be able to toggle deep links of an offering.
        """
        staff = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=staff.username, password="password")
        offering = factories.OfferingFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/offerings/{offering.id}/toggle-deeplinks/",
            data={"is_active": True},
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_admin_api_offering_toggle_deeplink_get_method(self):
        """
        It should not be possible for an authenticated admin user to toggle deeplinks with the
        get method.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory()

        response = self.client.get(
            f"/api/v1.0/admin/offerings/{offering.id}/toggle-deeplinks/",
            data={"is_active": True},
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_admin_api_offering_toggle_deeplink_post_method(self):
        """
        It should not be possible for an authenticated admin user to toggle deeplinks with the
        post method.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory()

        response = self.client.post(
            f"/api/v1.0/admin/offerings/{offering.id}/toggle-deeplinks/",
            data={"is_active": True},
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_admin_api_offering_toggle_deeplink_put_method(self):
        """
        It should not be possible for an authenticated admin user to toggle deeplinks with the
        put method.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory()

        response = self.client.put(
            f"/api/v1.0/admin/offerings/{offering.id}/toggle-deeplinks/",
            data={"is_active": True},
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_admin_api_offering_toggle_deeplink_delete_method(self):
        """
        It should not be possible for an authenticated admin user to toggle deeplinks with the
        delete method.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory()

        response = self.client.delete(
            f"/api/v1.0/admin/offerings/{offering.id}/toggle-deeplinks/",
            data={"is_active": True},
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_admin_api_offering_toggle_deeplink_wrong_offering_id(self):
        """
        It should not be possible toggle deeplinks if the offering id does not exists.
        A 404 status code error should be returned.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.patch(
            "/api/v1.0/admin/offerings/unknow_id/toggle-deeplinks/",
            data={"is_active": True},
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_admin_api_offering_toggle_deeplink_authenticated_superuser(self):
        """
        Authenticated admin user should be able to toggle on and off the deep links
        of an offering.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        organization_1, organization_2 = factories.OrganizationFactory.create_batch(2)
        offering = factories.OfferingFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            organizations=[organization_1, organization_2],
        )
        [deeplink_1, deeplink_2] = factories.OfferingDeepLinkFactory.create_batch(
            2,
            offering=offering,
            is_active=True,
        )

        # Deactivate all deeplinks of offering
        response = self.client.patch(
            f"/api/v1.0/admin/offerings/{offering.id}/toggle-deeplinks/",
            data={"is_active": False},
            content_type="application/json",
        )

        deeplink_1.refresh_from_db()
        deeplink_2.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)

        # Activte all deeplinks of offering
        response = self.client.patch(
            f"/api/v1.0/admin/offerings/{offering.id}/toggle-deeplinks/",
            data={
                "is_active": True,
            },
            content_type="application/json",
        )

        deeplink_1.refresh_from_db()
        deeplink_2.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertTrue(deeplink_1.is_active)
        self.assertTrue(deeplink_2.is_active)
