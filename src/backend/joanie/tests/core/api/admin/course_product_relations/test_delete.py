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

    def test_admin_api_course_products_relation_delete_anonymous(self):
        """
        Anonymous users should not be able to delete a course product relation.
        """
        relation = factories.CourseProductRelationFactory()
        response = self.client.delete(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )
        relation.refresh_from_db()
        self.assertIsNotNone(relation)

    def test_admin_api_course_products_relation_delete_authenticated(self):
        """
        Authenticated users should not be able to delete a course product relation.
        """
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        relation = factories.CourseProductRelationFactory()
        response = self.client.delete(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "You do not have permission to perform this action."},
        )
        relation.refresh_from_db()
        self.assertIsNotNone(relation)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_course_products_relation_delete_superuser(self, _):
        """
        Super admin user should be able to delete a course product relation.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        relation = factories.CourseProductRelationFactory()
        response = self.client.delete(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        with self.assertRaises(models.CourseProductRelation.DoesNotExist):
            relation.refresh_from_db()

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_course_products_relation_delete_restrict(self, _):
        """
        Order group with an existing order should not be deleted.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        relation = factories.CourseProductRelationFactory()
        order_group = factories.OrderGroupFactory(
            course_product_relation=relation,
        )
        factories.OrderFactory(
            order_groups=[order_group],
            product=relation.product,
            course=relation.course,
        )
        response = self.client.delete(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertDictEqual(
            response.json(),
            {"detail": "['You cannot delete this course product relation.']"},
        )
        relation.refresh_from_db()
        self.assertIsNotNone(relation)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_admin_api_course_products_relation_delete_order_group(self, _):
        """
        Order groups without an existing order should be deleted
        when deleting a course product relation.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        relation = factories.CourseProductRelationFactory()
        order_group = factories.OrderGroupFactory(
            course_product_relation=relation,
        )
        response = self.client.delete(
            f"/api/v1.0/admin/course-product-relations/{relation.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        with self.assertRaises(models.CourseProductRelation.DoesNotExist):
            relation.refresh_from_db()
        with self.assertRaises(models.OrderGroup.DoesNotExist):
            order_group.refresh_from_db()
