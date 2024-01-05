"""Test suite for the admin orders API endpoints."""
from http import HTTPStatus

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories
from joanie.tests import format_date


class OrdersAdminApiTestCase(TestCase):
    """Test suite for the admin orders API endpoints."""

    maxDiff = None

    def test_api_admin_orders_request_without_authentication(self):
        """
        Anonymous users should not be able to request orders endpoint.
        """
        response = self.client.get("/api/v1.0/admin/orders/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_api_admin_orders_request_with_lambda_user(self):
        """
        Lambda user should not be able to request orders endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_api_admin_orders_list(self):
        """Authenticated admin user should be able to list all existing orders."""
        # Create two orders, one linked to a course, the other linked to an enrollment
        course = factories.CourseFactory()
        orders = [
            factories.OrderFactory(),
            factories.OrderFactory(
                enrollment=factories.EnrollmentFactory(course_run__course=course),
                course=None,
                product__type=enums.PRODUCT_TYPE_CERTIFICATE,
                product__courses=[course],
            ),
        ]

        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        with self.assertNumQueries(4):
            response = self.client.get("/api/v1.0/admin/orders/")

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        expected_content = {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "course_code": order.course.code if order.course else None,
                    "created_on": format_date(order.created_on),
                    "enrollment_id": str(order.enrollment.id)
                    if order.enrollment
                    else None,
                    "id": str(order.id),
                    "organization_title": order.organization.title,
                    "owner_username": order.owner.username,
                    "product_title": order.product.title,
                    "state": order.state,
                    "total": float(order.total),
                    "total_currency": settings.DEFAULT_CURRENCY,
                }
                for order in sorted(orders, key=lambda x: x.created_on, reverse=True)
            ],
        }

        self.assertEqual(content, expected_content)

    def test_api_admin_orders_retrieve(self):
        """An admin user should be able to retrieve a single order through its id."""

        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create a "completed" order linked to a credential product with a certificate
        # definition
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__certificate_definition=factories.CertificateDefinitionFactory(),
        )
        order_group = factories.OrderGroupFactory(course_product_relation=relation)
        order = factories.OrderFactory(
            course=relation.course,
            product=relation.product,
            order_group=order_group,
            organization=relation.organizations.first(),
            state=enums.ORDER_STATE_VALIDATED,
        )

        # Create certificate
        factories.OrderCertificateFactory(
            order=order, certificate_definition=order.product.certificate_definition
        )

        # Create signed contract
        factories.ContractFactory(
            order=order,
            student_signed_on=order.created_on,
            organization_signed_on=order.created_on,
        )

        with self.assertNumQueries(16):
            response = self.client.get(f"/api/v1.0/admin/orders/{order.id}/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "id": str(order.id),
                "created_on": format_date(order.created_on),
                "state": order.state,
                "owner": {
                    "id": str(order.owner.id),
                    "username": order.owner.username,
                    "full_name": order.owner.get_full_name(),
                },
                "product_title": order.product.title,
                "enrollment": None,
                "course": {
                    "id": str(order.course.id),
                    "code": order.course.code,
                    "title": order.course.title,
                    "state": {
                        "priority": order.course.state["priority"],
                        "datetime": format_date(order.course.state["datetime"]),
                        "call_to_action": order.course.state["call_to_action"],
                        "text": order.course.state["text"],
                    },
                },
                "organization": {
                    "id": str(order.organization.id),
                    "code": order.organization.code,
                    "title": order.organization.title,
                },
                "order_group": {
                    "id": str(order_group.id),
                    "nb_seats": order_group.nb_seats,
                    "is_active": order_group.is_active,
                    "nb_available_seats": order_group.nb_seats
                    - order_group.get_nb_binding_orders(),
                    "created_on": format_date(order_group.created_on),
                    "can_edit": order_group.can_edit,
                },
                "total": float(order.total),
                "total_currency": settings.DEFAULT_CURRENCY,
                "contract": {
                    "id": str(order.contract.id),
                    "definition_title": order.contract.definition.title,
                    "student_signed_on": format_date(order.contract.student_signed_on),
                    "organization_signed_on": format_date(
                        order.contract.student_signed_on
                    ),
                    "submitted_for_signature_on": None,
                },
                "certificate": {
                    "id": str(order.certificate.id),
                    "definition_title": order.certificate.certificate_definition.title,
                    "issued_on": format_date(order.certificate.issued_on),
                },
                "main_invoice": {
                    "balance": float(order.main_invoice.balance),
                    "created_on": format_date(order.main_invoice.created_on),
                    "state": order.main_invoice.state,
                    "recipient_address": (
                        f"{order.main_invoice.recipient_address.full_name}\n"
                        f"{order.main_invoice.recipient_address.full_address}"
                    ),
                    "reference": order.main_invoice.reference,
                    "type": order.main_invoice.type,
                    "updated_on": format_date(order.main_invoice.updated_on),
                },
            },
        )

    def test_api_admin_orders_create(self):
        """Create an order should be not allowed."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.post("/api/v1.0/admin/orders/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_update(self):
        """Update an order should be not allowed."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        order = factories.OrderFactory()

        response = self.client.put(f"/api/v1.0/admin/orders/{order.id}/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_partial_update(self):
        """Update partially an order should be not allowed."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        order = factories.OrderFactory()

        response = self.client.patch(f"/api/v1.0/admin/orders/{order.id}/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_delete(self):
        """Delete an order should be not allowed."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        order = factories.OrderFactory()

        response = self.client.delete(f"/api/v1.0/admin/orders/{order.id}/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
