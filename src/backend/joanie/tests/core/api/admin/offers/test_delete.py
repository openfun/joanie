"""
Test suite for CourseProductRelation delete Admin API.
"""

from http import HTTPStatus
from unittest import mock

from django.test import TestCase

from joanie.core import factories, models
from joanie.core.serializers import fields


class CourseProductRelationDeleteAdminApiTest(TestCase):
    """
    Test suite for CourseProductRelation delete Admin API.
    """

    maxDiff = None

    def test_admin_api_offer_delete_anonymous(self):
        """
        Anonymous users should not be able to delete an offer.
        """
        offer = factories.OfferFactory()
        response = self.client.delete(
            f"/api/v1.0/admin/offers/{offer.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )
        offer.refresh_from_db()
        self.assertIsNotNone(offer)

    def test_admin_api_offer_delete_authenticated(self):
        """
        Authenticated users should not be able to delete an offer.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        offer = factories.OfferFactory()
        response = self.client.delete(
            f"/api/v1.0/admin/offers/{offer.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "You do not have permission to perform this action."},
        )
        offer.refresh_from_db()
        self.assertIsNotNone(offer)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_offer_delete_superuser(self, _):
        """
        Super admin user should be able to delete an offer.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offer = factories.OfferFactory()
        response = self.client.delete(
            f"/api/v1.0/admin/offers/{offer.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        with self.assertRaises(models.CourseProductRelation.DoesNotExist):
            offer.refresh_from_db()

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_offer_delete_restrict(self, _):
        """
        Offer rule with an existing order should not be deleted.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offer = factories.OfferFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=offer,
        )
        factories.OrderFactory(
            offer_rules=[offer_rule],
            product=offer.product,
            course=offer.course,
        )
        response = self.client.delete(
            f"/api/v1.0/admin/offers/{offer.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "['You cannot delete this offer.']"},
        )
        offer.refresh_from_db()
        self.assertIsNotNone(offer)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_offer_delete_offer_rule(self, _):
        """
        Offer rules without an existing order should be deleted
        when deleting an offer.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offer = factories.OfferFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=offer,
        )
        response = self.client.delete(
            f"/api/v1.0/admin/offers/{offer.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        with self.assertRaises(models.CourseProductRelation.DoesNotExist):
            offer.refresh_from_db()
        with self.assertRaises(models.OfferRule.DoesNotExist):
            offer_rule.refresh_from_db()
