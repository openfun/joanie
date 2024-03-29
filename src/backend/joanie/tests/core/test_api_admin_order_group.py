"""
Test suite for OrderGroup Admin API.
"""

from http import HTTPStatus
from operator import itemgetter

from django.test import TestCase

from joanie.core import factories, models


class OrderGroupAdminApiTest(TestCase):
    """
    Test suite for OrderGroup Admin API.
    """

    base_url = "/api/v1.0/admin/course-product-relations"

    # list
    def test_admin_api_order_group_list_anonymous(self):
        """
        Anonymous users should not be able to list order groups.
        """

        relation = factories.CourseProductRelationFactory()
        response = self.client.get(f"{self.base_url}/{relation.id}/order-groups/")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_order_group_list_authenticated(self):
        """
        Authenticated users should be able to list order groups.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        order_groups = factories.OrderGroupFactory.create_batch(
            3, course_product_relation=relation
        )
        factories.OrderGroupFactory.create_batch(5)

        with self.assertNumQueries(10):
            response = self.client.get(f"{self.base_url}/{relation.id}/order-groups/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        expected_return = [
            {
                "id": str(order_group.id),
                "nb_seats": order_group.nb_seats,
                "is_active": order_group.is_active,
                "nb_available_seats": order_group.nb_seats
                - order_group.get_nb_binding_orders(),
                "created_on": order_group.created_on.isoformat().replace("+00:00", "Z"),
                "can_edit": True,
            }
            for order_group in order_groups
        ]
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            content["results"],
            sorted(expected_return, key=itemgetter("created_on")),
        )

    def test_admin_api_order_group_list_lambda_user(self):
        """
        Non admin user should not be able to request order groups endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")
        relation = factories.CourseProductRelationFactory()

        response = self.client.get(f"{self.base_url}/{relation.id}/order-groups/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    # details
    def test_admin_api_order_group_retrieve_anonymous(self):
        """
        Anonymous users should not be able to request order groups details.
        """

        relation = factories.CourseProductRelationFactory()
        order_group = factories.OrderGroupFactory(course_product_relation=relation)

        response = self.client.get(
            f"{self.base_url}/{relation.id}/order-groups/{order_group.id}/"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_order_group_retrieve_authenticated(self):
        """
        Authenticated users should be able to request order groups details.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        order_group = factories.OrderGroupFactory(course_product_relation=relation)

        with self.assertNumQueries(5):
            response = self.client.get(
                f"{self.base_url}/{relation.id}/order-groups/{order_group.id}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        expected_return = {
            "id": str(order_group.id),
            "nb_seats": order_group.nb_seats,
            "is_active": order_group.is_active,
            "nb_available_seats": order_group.nb_seats
            - order_group.get_nb_binding_orders(),
            "created_on": order_group.created_on.isoformat().replace("+00:00", "Z"),
            "can_edit": True,
        }
        self.assertEqual(content, expected_return)

    # create
    def test_admin_api_order_group_create_anonymous(self):
        """
        Anonymous users should not be able to create an order groups.
        """
        relation = factories.CourseProductRelationFactory()

        data = {"nb_seats": 5, "is_active": True}
        response = self.client.post(
            f"{self.base_url}/{relation.id}/order-groups/",
            content_type="application/json",
            data=data,
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_order_group_create_authenticated(self):
        """
        Authenticated users should be able to request order groups list.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        data = {
            "nb_seats": 5,
            "is_active": True,
        }
        with self.assertNumQueries(6):
            response = self.client.post(
                f"{self.base_url}/{relation.id}/order-groups/",
                content_type="application/json",
                data=data,
            )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()
        self.assertEqual(content["nb_seats"], data["nb_seats"])
        self.assertEqual(content["is_active"], data["is_active"])
        self.assertEqual(models.OrderGroup.objects.filter(**data).count(), 1)

    # update
    def test_admin_api_order_group_update_anonymous(self):
        """
        Anonymous users should not be able to update order groups.
        """

        relation = factories.CourseProductRelationFactory()
        order_group = factories.OrderGroupFactory(course_product_relation=relation)

        response = self.client.put(
            f"{self.base_url}/{relation.id}/order-groups/{order_group.id}/"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_order_group_update_authenticated(self):
        """
        Authenticated users should be able to update order groups.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        order_group = factories.OrderGroupFactory(course_product_relation=relation)
        data = {
            "nb_seats": 505,
            "is_active": True,
        }
        with self.assertNumQueries(6):
            response = self.client.put(
                f"{self.base_url}/{relation.id}/order-groups/{str(order_group.id)}/",
                content_type="application/json",
                data=data,
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["nb_seats"], data["nb_seats"])
        self.assertEqual(content["is_active"], data["is_active"])
        self.assertEqual(models.OrderGroup.objects.filter(**data).count(), 1)

    # patch
    def test_admin_api_order_group_patch_anonymous(self):
        """
        Anonymous users should not be able to patch order groups.
        """

        relation = factories.CourseProductRelationFactory()
        order_group = factories.OrderGroupFactory(course_product_relation=relation)

        response = self.client.patch(
            f"{self.base_url}/{relation.id}/order-groups/{order_group.id}/"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_order_group_patch_authenticated(self):
        """
        Authenticated users should be able to patch order groups.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        order_group = factories.OrderGroupFactory(
            course_product_relation=relation, is_active=False
        )
        data = {
            "is_active": True,
        }
        with self.assertNumQueries(6):
            response = self.client.patch(
                f"{self.base_url}/{relation.id}/order-groups/{str(order_group.id)}/",
                content_type="application/json",
                data=data,
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["nb_seats"], order_group.nb_seats)
        self.assertEqual(content["is_active"], data["is_active"])
        self.assertEqual(
            models.OrderGroup.objects.filter(
                nb_seats=order_group.nb_seats, **data
            ).count(),
            1,
        )

    # delete
    def test_admin_api_order_group_delete_anonymous(self):
        """
        Anonymous users should not be able to delete order groups.
        """

        relation = factories.CourseProductRelationFactory()
        order_group = factories.OrderGroupFactory(course_product_relation=relation)

        response = self.client.delete(
            f"{self.base_url}/{relation.id}/order-groups/{order_group.id}/"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        with self.assertNumQueries(0):
            self.assertEqual(
                content["detail"], "Authentication credentials were not provided."
            )

    def test_admin_api_order_group_delete_authenticated(self):
        """
        Authenticated users should not be able to delete order groups.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        order_group = factories.OrderGroupFactory(course_product_relation=relation)
        with self.assertNumQueries(5):
            response = self.client.delete(
                f"{self.base_url}/{relation.id}/order-groups/{order_group.id}/",
            )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(models.OrderGroup.objects.filter(id=order_group.id).exists())

    def test_admin_api_order_group_delete_cannot_edit(self):
        """
        Deleting an order group that cannot be edited should fail.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        order_group = factories.OrderGroupFactory(course_product_relation=relation)
        with self.assertNumQueries(5):
            response = self.client.delete(
                f"{self.base_url}/{relation.id}/order-groups/{order_group.id}/",
            )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(models.OrderGroup.objects.filter(id=order_group.id).exists())
