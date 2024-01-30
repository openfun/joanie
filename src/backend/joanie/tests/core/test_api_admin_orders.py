"""Test suite for the admin orders API endpoints."""
import uuid
from decimal import Decimal as D
from http import HTTPStatus

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories
from joanie.core.models import Order
from joanie.payment.factories import InvoiceFactory
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
                    "owner_name": order.owner.username,
                    "product_title": order.product.title,
                    "state": order.state,
                    "total": float(order.total),
                    "total_currency": settings.DEFAULT_CURRENCY,
                }
                for order in sorted(orders, key=lambda x: x.created_on, reverse=True)
            ],
        }

        self.assertEqual(content, expected_content)

    def test_api_admin_orders_list_filter_by_course_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        one or several course_id
        """
        orders = factories.OrderFactory.create_batch(2)
        # - Create random orders
        factories.OrderFactory.create_batch(2)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 4)

        for order in orders:
            response = self.client.get(
                f"/api/v1.0/admin/orders/?course_ids={order.course.id}"
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

        response = self.client.get(
            f"/api/v1.0/admin/orders/"
            f"?course_ids={orders[0].course.id}"
            f"&course_ids={orders[1].course.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        unknown_id = uuid.uuid4()
        response = self.client.get(f"/api/v1.0/admin/orders/?course_ids={unknown_id}")
        self.assertContains(
            response,
            f'{{"course_ids":["'
            f"Select a valid choice. {unknown_id} is not one of the available choices."
            f'"]}}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_invalid_course_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        course_id and get a bad request if the course id is not a valid uuid
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/?course_ids=invalid")

        self.assertContains(
            response,
            '{"course_ids":["“invalid” is not a valid UUID."]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_product_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        one or several product_id
        """
        orders = factories.OrderFactory.create_batch(2)
        # - Create random orders
        factories.OrderFactory.create_batch(2)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 4)

        for order in orders:
            response = self.client.get(
                f"/api/v1.0/admin/orders/?product_ids={order.product.id}"
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

        # - Filter by several product ids
        response = self.client.get(
            f"/api/v1.0/admin/orders/"
            f"?product_ids={orders[0].product.id}"
            f"&product_ids={orders[1].product.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        unknown_id = uuid.uuid4()
        response = self.client.get(f"/api/v1.0/admin/orders/?product_ids={unknown_id}")
        self.assertContains(
            response,
            f'{{"product_ids":["'
            f"Select a valid choice. {unknown_id} is not one of the available choices."
            f'"]}}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_invalid_product_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        product_ids and get a bad request if the product id is not a valid uuid
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/?product_ids=invalid")

        self.assertContains(
            response,
            '{"product_ids":["“invalid” is not a valid UUID."]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_organization_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        one or several organization id
        """
        orders = factories.OrderFactory.create_batch(2)
        # - Create random orders
        factories.OrderFactory.create_batch(2)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 4)

        for order in orders:
            response = self.client.get(
                f"/api/v1.0/admin/orders/?organization_ids={order.organization.id}"
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

        # - Filter by several organization id
        response = self.client.get(
            f"/api/v1.0/admin/orders/"
            f"?organization_ids={orders[0].organization.id}"
            f"&organization_ids={orders[1].organization.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        unknown_id = uuid.uuid4()
        response = self.client.get(
            f"/api/v1.0/admin/orders/?organization_ids={unknown_id}"
        )
        self.assertContains(
            response,
            f'{{"organization_ids":["'
            f"Select a valid choice. {unknown_id} is not one of the available choices."
            f'"]}}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_invalid_organization_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        organization_id and get a bad request if the organization id is not a valid uuid
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/?organization_ids=invalid")

        self.assertContains(
            response,
            '{"organization_ids":["“invalid” is not a valid UUID."]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_owner_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        one or several owner_id
        """
        orders = factories.OrderFactory.create_batch(2)
        # - Create random orders
        factories.OrderFactory.create_batch(2)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 4)

        for order in orders:
            response = self.client.get(
                f"/api/v1.0/admin/orders/?owner_ids={order.owner.id}"
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

        # - Filter by several owner id
        response = self.client.get(
            f"/api/v1.0/admin/orders/"
            f"?owner_ids={orders[0].owner.id}"
            f"&owner_ids={orders[1].owner.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        unknown_id = uuid.uuid4()
        response = self.client.get(f"/api/v1.0/admin/orders/?owner_ids={unknown_id}")
        self.assertContains(
            response,
            f'{{"owner_ids":["'
            f"Select a valid choice. {unknown_id} is not one of the available choices."
            f'"]}}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_invalid_owner_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        owner_id and get a bad request if the owner id is not a valid uuid
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/?owner_ids=invalid")

        self.assertContains(
            response,
            '{"owner_ids":["“invalid” is not a valid UUID."]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_state(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        state
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        for [state, _] in enums.ORDER_STATE_CHOICES:
            factories.OrderFactory(state=state)

        for [state, _] in enums.ORDER_STATE_CHOICES:
            response = self.client.get(f"/api/v1.0/admin/orders/?state={state}")
            order = Order.objects.get(state=state)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

    def test_api_admin_orders_list_filter_by_invalid_state(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        state and get a bad request if the state is not a valid choice
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.get("/api/v1.0/admin/orders/?state=invalid_state")

        self.assertContains(
            response,
            '{"state":["'
            "Select a valid choice. invalid_state is not one of the available choices."
            '"]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_query_language(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        a query. This query should allow to search order on owner, product, course and
        organization.
        """
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # - Create random orders
        factories.OrderFactory.create_batch(2)

        # - Create an order to test the query filter
        course = factories.CourseFactory(
            title="Introduction to resource filtering",
            code="C_101",
        )
        course.translations.create(
            language_code="fr-fr", title="Introduction au filtrage de resource"
        )

        product = factories.ProductFactory(
            title="Micro credential",
        )
        product.translations.create(language_code="fr-fr", title="Micro certification")

        organization = factories.OrganizationFactory(
            title="Acme University", code="U_ACME"
        )
        organization.translations.create(language_code="fr-fr", title="Université Acme")

        factories.CourseProductRelationFactory(
            organizations=[organization],
            course=course,
            product=product,
        )
        order = factories.OrderFactory(
            owner=factories.UserFactory(
                username="jo_cun",
                first_name="Joanie",
                last_name="Cunningham",
                email="jo_cun@example.com",
            ),
            product=product,
            course=course,
            organization=organization,
        )

        response = self.client.get("/api/v1.0/admin/orders/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)

        # Prepare queries to test
        # - Queries related to owner (username, first_name, last_name, email)
        queries = [
            "jo_cun",
            "jo_",
            "Joanie",
            "oani",
            "Cunningham",
            "nning",
            "jo_cun@example.com",
            "_cun@examp",
        ]
        # - Queries related to product (title in any language))
        queries += [
            "Micro credential",
            "credential",
            "Micro certification",
            "certification",
        ]
        # - Queries related to course (code, title in any language)
        queries += [
            "Introduction to resource filtering",
            "Introduction au filtrage de resource",
            "Introduction",
            "resource",
            "C_101",
        ]
        # - Queries related to organization (code, title in any language)
        queries += [
            "Acme University",
            "Université Acme",
            "Acme",
            "U_ACME",
        ]

        for query in queries:
            response = self.client.get(f"/api/v1.0/admin/orders/?query={query}")
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

    def test_api_admin_orders_course_retrieve(self):
        """An admin user should be able to retrieve a single course order through its id."""

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

        # Create a credit note
        credit_note = InvoiceFactory(
            parent=order.main_invoice,
            total=D("1.00"),
        )

        with self.assertNumQueries(29):
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
                    "email": order.owner.email,
                },
                "product": {
                    "call_to_action": "let's go!",
                    "certificate_definition": str(
                        relation.product.certificate_definition.id
                    ),
                    "contract_definition": str(relation.product.contract_definition.id),
                    "description": relation.product.description,
                    "id": str(relation.product.id),
                    "price": float(relation.product.price),
                    "price_currency": "EUR",
                    "target_courses": [],
                    "title": relation.product.title,
                    "type": "credential",
                },
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
                    "id": str(order.main_invoice.id),
                    "balance": float(order.main_invoice.balance),
                    "created_on": format_date(order.main_invoice.created_on),
                    "state": order.main_invoice.state,
                    "children": [
                        {
                            "id": str(credit_note.id),
                            "balance": float(credit_note.balance),
                            "created_on": format_date(credit_note.created_on),
                            "invoiced_balance": float(credit_note.invoiced_balance),
                            "recipient_address": (
                                f"{credit_note.recipient_address.full_name}\n"
                                f"{credit_note.recipient_address.full_address}"
                            ),
                            "reference": credit_note.reference,
                            "state": credit_note.state,
                            "transactions_balance": float(
                                credit_note.transactions_balance
                            ),
                            "total": float(credit_note.total),
                            "total_currency": settings.DEFAULT_CURRENCY,
                            "type": credit_note.type,
                            "updated_on": format_date(credit_note.updated_on),
                        }
                    ],
                    "invoiced_balance": float(order.main_invoice.invoiced_balance),
                    "recipient_address": (
                        f"{order.main_invoice.recipient_address.full_name}\n"
                        f"{order.main_invoice.recipient_address.full_address}"
                    ),
                    "reference": order.main_invoice.reference,
                    "transactions_balance": float(
                        order.main_invoice.transactions_balance
                    ),
                    "total": float(order.main_invoice.total),
                    "total_currency": settings.DEFAULT_CURRENCY,
                    "type": order.main_invoice.type,
                    "updated_on": format_date(order.main_invoice.updated_on),
                },
            },
        )

    def test_api_admin_orders_enrollment_retrieve(self):
        """An admin user should be able to retrieve a single enrollment order through its id."""

        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create a "completed" order linked to a certificate product with a certificate
        # definition
        course = factories.CourseFactory()
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            product__certificate_definition=factories.CertificateDefinitionFactory(),
            course=course,
        )

        enrollment = factories.EnrollmentFactory(course_run__course=course)
        order = factories.OrderFactory(
            enrollment=enrollment,
            course=None,
            product=relation.product,
            organization=relation.organizations.first(),
            state=enums.ORDER_STATE_VALIDATED,
        )

        # Create certificate
        factories.OrderCertificateFactory(
            order=order, certificate_definition=order.product.certificate_definition
        )

        with self.assertNumQueries(14):
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
                    "email": order.owner.email,
                },
                "product": {
                    "call_to_action": "let's go!",
                    "certificate_definition": str(
                        relation.product.certificate_definition.id
                    ),
                    "contract_definition": None,
                    "description": relation.product.description,
                    "id": str(relation.product.id),
                    "price": float(relation.product.price),
                    "price_currency": "EUR",
                    "target_courses": [],
                    "title": relation.product.title,
                    "type": "certificate",
                },
                "enrollment": {
                    "id": str(enrollment.id),
                    "created_on": format_date(enrollment.created_on),
                    "updated_on": format_date(enrollment.updated_on),
                    "state": enrollment.state,
                    "is_active": enrollment.is_active,
                    "was_created_by_order": enrollment.was_created_by_order,
                    "course_run": {
                        "id": str(enrollment.course_run.id),
                        "start": format_date(enrollment.course_run.start),
                        "end": format_date(enrollment.course_run.end),
                        "enrollment_start": format_date(
                            enrollment.course_run.enrollment_start
                        ),
                        "enrollment_end": format_date(
                            enrollment.course_run.enrollment_end
                        ),
                        "languages": enrollment.course_run.languages,
                        "title": enrollment.course_run.title,
                        "is_gradable": enrollment.course_run.is_gradable,
                        "is_listed": enrollment.course_run.is_listed,
                        "resource_link": enrollment.course_run.resource_link,
                        "state": {
                            "call_to_action": enrollment.course_run.state.get(
                                "call_to_action"
                            ),
                            "datetime": format_date(
                                enrollment.course_run.state.get("datetime")
                            ),
                            "priority": enrollment.course_run.state.get("priority"),
                            "text": enrollment.course_run.state.get("text"),
                        },
                        "uri": enrollment.course_run.uri,
                    },
                },
                "course": None,
                "organization": {
                    "id": str(order.organization.id),
                    "code": order.organization.code,
                    "title": order.organization.title,
                },
                "order_group": None,
                "total": float(order.total),
                "total_currency": settings.DEFAULT_CURRENCY,
                "contract": None,
                "certificate": {
                    "id": str(order.certificate.id),
                    "definition_title": order.certificate.certificate_definition.title,
                    "issued_on": format_date(order.certificate.issued_on),
                },
                "main_invoice": {
                    "id": str(order.main_invoice.id),
                    "balance": float(order.main_invoice.balance),
                    "created_on": format_date(order.main_invoice.created_on),
                    "state": order.main_invoice.state,
                    "children": [],
                    "invoiced_balance": float(order.main_invoice.invoiced_balance),
                    "recipient_address": (
                        f"{order.main_invoice.recipient_address.full_name}\n"
                        f"{order.main_invoice.recipient_address.full_address}"
                    ),
                    "reference": order.main_invoice.reference,
                    "transactions_balance": float(
                        order.main_invoice.transactions_balance
                    ),
                    "total": float(order.main_invoice.total),
                    "total_currency": settings.DEFAULT_CURRENCY,
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
