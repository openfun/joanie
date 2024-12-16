"""Test suite for the admin orders API export endpoint."""

from http import HTTPStatus
from unittest import mock

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from joanie.core import factories
from joanie.core.models import Order
from joanie.tests import format_date_export
from joanie.tests.testing_utils import Demo


def yes_no(value):
    """Return "Oui" if value is True, "Non" otherwise."""
    return "Oui" if value else "Non"


def expected_csv_content(order):
    """Return the expected CSV content for an order."""
    content = {
        "Référence de commande": str(order.id),
        "Produit": order.product.title,
        "Propriétaire": order.owner.get_full_name(),
        "Email": order.owner.email,
        "Établissement": order.organization.title,
        "État de la commande": order.state,
        "Date de création": format_date_export(order.created_on),
        "Date de dernière modification": format_date_export(order.updated_on),
        "Type de produit": order.product.type,
        "Session d'inscription": "",
        "Statut de la session": "",
        "Inscrit le": "",
        "Prix": str(order.total),
        "Devise": settings.DEFAULT_CURRENCY,
        "Renoncement au délai de rétractation": yes_no(
            order.has_waived_withdrawal_right
        ),
        "Certificat généré pour cette commande": yes_no(hasattr(order, "certificate")),
        "Contrat": "",
        "Soumis pour signature": "",
        "Date de signature de l'apprenant": "",
        "Date de signature de l'établissement": "",
        "Type": "",
        "Total (sur la facture)": "",
        "Solde (sur la facture)": "",
        "État de facturation": "",
        "Type de carte": order.credit_card.brand,
        "Derniers chiffres de la carte bancaire": order.credit_card.last_numbers,
        "Date d'expiration de la carte bancaire": (
            f"{order.credit_card.expiration_month}/{order.credit_card.expiration_year}"
        ),
    }

    for i in range(1, 5):
        content[f"Date de paiement {i}"] = ""
        content[f"Montant du paiement {i}"] = ""
        content[f"État du paiement {i}"] = ""

    if order.enrollment:
        content["Session d'inscription"] = order.enrollment.course_run.title
        content["Statut de la session"] = str(order.enrollment.course_run.state)
        content["Inscrit le"] = format_date_export(order.enrollment.created_on)

    if hasattr(order, "contract"):
        content["Contrat"] = order.contract.definition.title
        content["Soumis pour signature"] = format_date_export(
            order.contract.submitted_for_signature_on
        )
        content["Date de signature de l'apprenant"] = format_date_export(
            order.contract.student_signed_on
        )
        content["Date de signature de l'établissement"] = format_date_export(
            order.contract.organization_signed_on
        )

    if order.main_invoice:
        content["Type"] = order.main_invoice.type
        content["Total (sur la facture)"] = str(order.main_invoice.total)
        content["Solde (sur la facture)"] = str(order.main_invoice.balance)
        content["État de facturation"] = order.main_invoice.state

    for i, installment in enumerate(order.payment_schedule, start=1):
        content[f"Date de paiement {i}"] = format_date_export(
            installment.get("due_date")
        )
        content[f"Montant du paiement {i}"] = str(installment.get("amount"))
        content[f"État du paiement {i}"] = installment.get("state")

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
