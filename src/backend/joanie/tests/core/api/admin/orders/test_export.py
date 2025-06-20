"""Test suite for the admin orders API export endpoint."""

from http import HTTPStatus
from unittest import mock

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import Course, Order
from joanie.tests import format_date_export
from joanie.tests.testing_utils import Demo


def yes_no(value):
    """Return "Yes" if value is True, "No" otherwise."""
    return "Yes" if value else "No"


def expected_csv_content(order):
    """Return the expected CSV content for an order."""
    content = {
        "Order reference": str(order.id),
        "Product": order.product.title,
        "Owner": order.owner.get_full_name(),
        "Email": order.owner.email,
        "Organization": order.organization.title,
        "Order state": order.state,
        "Creation date": format_date_export(order.created_on),
        "Last modification date": format_date_export(order.updated_on),
        "Product type": order.product.type,
        "Enrollment session": "",
        "Session status": "",
        "Enrolled on": "",
        "Price": str(order.total),
        "Currency": settings.DEFAULT_CURRENCY,
        "Discount": "",
        "Waived withdrawal right": yes_no(order.has_waived_withdrawal_right),
        "Certificate generated for this order": yes_no(hasattr(order, "certificate")),
        "Contract": "",
        "Submitted for signature": "",
        "Student signature date": "",
        "Organization signature date": "",
        "Type": "",
        "Total (on invoice)": "",
        "Balance (on invoice)": "",
        "Billing state": "",
        "Card type": order.credit_card.brand,
        "Last card digits": order.credit_card.last_numbers,
        "Card expiration date": (
            f"{order.credit_card.expiration_month}/{order.credit_card.expiration_year}"
        ),
    }

    for i in range(1, 5):
        content[f"Installment date {i}"] = ""
        content[f"Installment amount {i}"] = ""
        content[f"Installment state {i}"] = ""

    if order.enrollment:
        content["Enrollment session"] = order.enrollment.course_run.title
        content["Session status"] = str(order.enrollment.course_run.state)
        content["Enrolled on"] = format_date_export(order.enrollment.created_on)

    if hasattr(order, "contract"):
        content["Contract"] = order.contract.definition.title
        content["Submitted for signature"] = format_date_export(
            order.contract.submitted_for_signature_on
        )
        content["Student signature date"] = format_date_export(
            order.contract.student_signed_on
        )
        content["Organization signature date"] = format_date_export(
            order.contract.organization_signed_on
        )

    if order.main_invoice:
        content["Type"] = order.main_invoice.type
        content["Total (on invoice)"] = str(order.main_invoice.total)
        content["Balance (on invoice)"] = str(order.main_invoice.balance)
        content["Billing state"] = order.main_invoice.state

    if order.discount:
        content["Discount"] = order.discount

    for i, installment in enumerate(order.payment_schedule, start=1):
        content[f"Installment date {i}"] = format_date_export(
            installment.get("due_date")
        )
        content[f"Installment amount {i}"] = str(installment.get("amount"))
        content[f"Installment state {i}"] = installment.get("state")

    return content


class OrdersAdminApiExportTestCase(TestCase):
    """Test suite for the admin orders API export endpoint."""

    maxDiff = None

    def test_api_admin_orders_export_csv_anonymous_user(self):
        """
        Anonymous users should not be able to export orders as CSV.
        """
        response = self.client.get("/api/v1.0/admin/orders/export/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_orders_export_csv_lambda_user(self):
        """
        Lambda users should not be able to export orders as CSV.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/export/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_api_admin_orders_export_csv(self):
        """
        Admin users should be able to export orders as CSV.
        """
        Demo().generate()

        orders = Order.objects.all()

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            response = self.client.get("/api/v1.0/admin/orders/export/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="orders_{now.strftime("%d-%m-%Y_%H-%M-%S")}.csv"',
        )

        csv_content = response.getvalue().decode().splitlines()
        csv_header = csv_content.pop(0)
        expected_headers = expected_csv_content(orders[0]).keys()

        self.assertEqual(csv_header.split(","), list(expected_headers))

        for order, csv_line in zip(orders, csv_content, strict=False):
            self.assertEqual(
                csv_line.split(","), list(expected_csv_content(order).values())
            )

    def test_api_admin_orders_export_csv_filter(self):
        """
        State filter should be applied when exporting orders as CSV.
        """
        Demo().generate()
        course_ids = Course.objects.filter(
            order__state=enums.ORDER_STATE_COMPLETED
        ).values_list("id", flat=True)[:2]

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get(
            f"/api/v1.0/admin/orders/export/?state={enums.ORDER_STATE_TO_SIGN}"
            f"&course_ids={course_ids[0]},{course_ids[1]}"
        )

        csv_content = response.getvalue().decode().splitlines()
        csv_content.pop(0)

        orders = Order.objects.filter(
            state=enums.ORDER_STATE_COMPLETED, course_id__in=course_ids
        )
        for order, csv_line in zip(orders, csv_content, strict=False):
            self.assertEqual(
                csv_line.split(","), list(expected_csv_content(order).values())
            )
