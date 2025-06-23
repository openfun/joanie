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

    def test_admin_api_offering_delete_anonymous(self):
        """
        Anonymous users should not be able to delete an offering.
        """
        offering = factories.OfferingFactory()
        response = self.client.delete(
            f"/api/v1.0/admin/offerings/{offering.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )
        offering.refresh_from_db()
        self.assertIsNotNone(offering)

    def test_admin_api_offering_delete_authenticated(self):
        """
        Authenticated users should not be able to delete an offering.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        offering = factories.OfferingFactory()
        response = self.client.delete(
            f"/api/v1.0/admin/offerings/{offering.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "You do not have permission to perform this action."},
        )
        offering.refresh_from_db()
        self.assertIsNotNone(offering)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_offering_delete_superuser(self, _):
        """
        Super admin user should be able to delete an offering.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory()
        response = self.client.delete(
            f"/api/v1.0/admin/offerings/{offering.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        with self.assertRaises(models.CourseProductRelation.DoesNotExist):
            offering.refresh_from_db()

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_offering_delete_restrict(self, _):
        """
        Offering rule with an existing order should not be deleted.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory()
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
        )
        factories.OrderFactory(
            offering_rules=[offering_rule],
            product=offering.product,
            course=offering.course,
        )
        response = self.client.delete(
            f"/api/v1.0/admin/offerings/{offering.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "['You cannot delete this offering.']"},
        )
        offering.refresh_from_db()
        self.assertIsNotNone(offering)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_offering_delete_offering_rule(self, _):
        """
        Offering rules without an existing order should be deleted
        when deleting an offering.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        offering = factories.OfferingFactory()
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
        )
        response = self.client.delete(
            f"/api/v1.0/admin/offerings/{offering.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        with self.assertRaises(models.CourseProductRelation.DoesNotExist):
            offering.refresh_from_db()
        with self.assertRaises(models.OfferingRule.DoesNotExist):
            offering_rule.refresh_from_db()
