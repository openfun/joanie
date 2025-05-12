"""Test suite for the admin orders API retrieve endpoint."""

from decimal import Decimal as D
from http import HTTPStatus

from django.conf import settings
from django.test import TestCase, override_settings

from joanie.core import enums, factories
from joanie.payment.factories import InvoiceFactory
from joanie.payment.models import Invoice
from joanie.tests import format_date


class OrdersAdminApiRetrieveTestCase(TestCase):
    """Test suite for the admin orders API retrieve endpoint."""

    maxDiff = None

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={100: (100,)},
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_admin_orders_course_retrieve(self):
        """An admin user should be able to retrieve a single course order through its id."""

        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create a "completed" order linked to a credential product with a certificate
        # definition
        relation = factories.CourseProductRelationFactory(
            product__price=100,
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__certificate_definition=factories.CertificateDefinitionFactory(),
        )
        order_group = factories.OrderGroupFactory(course_product_relation=relation)
        order = factories.OrderGeneratorFactory(
            course=relation.course,
            product=relation.product,
            order_groups=[order_group],
            organization=relation.organizations.first(),
            state=enums.ORDER_STATE_COMPLETED,
        )
        order.freeze_total()

        # Create certificate
        factories.OrderCertificateFactory(
            order=order, certificate_definition=order.product.certificate_definition
        )
        # Get the children invoice of the main invoice
        child_invoice = Invoice.objects.get(
            parent=order.main_invoice,
            order=order,
            transactions__reference__in=[str(order.payment_schedule[0]["id"])],
        )
        # Create a credit note
        credit_note = InvoiceFactory(
            parent=order.main_invoice,
            total=D("1.00"),
        )

        with self.assertNumQueries(41):
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
                    "target_courses": [str(order.course.id)],
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
                "order_groups": [
                    {
                        "id": str(order_group.id),
                        "description": order_group.description,
                        "nb_seats": order_group.nb_seats,
                        "is_active": order_group.is_active,
                        "is_enabled": order_group.is_enabled,
                        "nb_available_seats": order_group.nb_seats
                        - order_group.get_nb_binding_orders(),
                        "created_on": format_date(order_group.created_on),
                        "can_edit": order_group.can_edit,
                        "start": None,
                        "end": None,
                        "discount": None,
                    }
                ],
                "total": float(order.total),
                "total_currency": settings.DEFAULT_CURRENCY,
                "contract": {
                    "id": str(order.contract.id),
                    "definition_title": order.contract.definition.title,
                    "student_signed_on": format_date(order.contract.student_signed_on),
                    "organization_signed_on": format_date(
                        order.contract.organization_signed_on
                    ),
                    "submitted_for_signature_on": None,
                },
                "certificate": {
                    "id": str(order.certificate.id),
                    "definition_title": order.certificate.certificate_definition.title,
                    "issued_on": format_date(order.certificate.issued_on),
                },
                "payment_schedule": [
                    {
                        "id": str(installment["id"]),
                        "amount": float(installment["amount"]),
                        "currency": "EUR",
                        "due_date": format_date(installment["due_date"]),
                        "state": installment["state"],
                    }
                    for installment in order.payment_schedule
                ],
                "main_invoice": {
                    "id": str(order.main_invoice.id),
                    "balance": float(order.main_invoice.balance),
                    "created_on": format_date(order.main_invoice.created_on),
                    "state": order.main_invoice.state,
                    "children": [
                        {
                            "id": str(child_invoice.id),
                            "balance": float(child_invoice.balance),
                            "created_on": format_date(child_invoice.created_on),
                            "invoiced_balance": float(child_invoice.invoiced_balance),
                            "recipient_address": (
                                f"{child_invoice.recipient_address.full_name}\n"
                                f"{child_invoice.recipient_address.full_address}"
                            ),
                            "reference": child_invoice.reference,
                            "state": child_invoice.state,
                            "transactions_balance": float(
                                child_invoice.transactions_balance
                            ),
                            "total": float(child_invoice.total),
                            "total_currency": settings.DEFAULT_CURRENCY,
                            "type": child_invoice.type,
                            "updated_on": format_date(child_invoice.updated_on),
                        },
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
                        },
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
                "credit_card": None,
                "has_waived_withdrawal_right": order.has_waived_withdrawal_right,
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
            state=enums.ORDER_STATE_COMPLETED,
        )

        # Create certificate
        factories.OrderCertificateFactory(
            order=order, certificate_definition=order.product.certificate_definition
        )

        with self.assertNumQueries(15):
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
                "order_groups": [],
                "total": float(order.total),
                "total_currency": settings.DEFAULT_CURRENCY,
                "contract": None,
                "certificate": {
                    "id": str(order.certificate.id),
                    "definition_title": order.certificate.certificate_definition.title,
                    "issued_on": format_date(order.certificate.issued_on),
                },
                "payment_schedule": [],
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
                "credit_card": {
                    "id": str(order.credit_card.id),
                    "last_numbers": order.credit_card.last_numbers,
                    "brand": order.credit_card.brand,
                    "expiration_month": order.credit_card.expiration_month,
                    "expiration_year": order.credit_card.expiration_year,
                },
                "has_waived_withdrawal_right": order.has_waived_withdrawal_right,
            },
        )
