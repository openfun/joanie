"""Invoice admin test suite"""
from django.test import TestCase
from django.urls import reverse

import lxml.html

from joanie.core import enums, factories
from joanie.payment.factories import InvoiceFactory, TransactionFactory


class InvoiceAdminTestCase(TestCase):
    """Invoice admin tests"""

    def test_admin_invoice_display_human_readable_type(self):
        """
        Invoice admin view should display
        invoice type in a human-readable manner.
        """
        # - Login as admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # - Create an order with a related invoice
        order = factories.OrderFactory(state=enums.ORDER_STATE_VALIDATED)
        credit_note = InvoiceFactory(
            order=order, parent=order.main_invoice, total=-order.total
        )

        # - Now go to the invoice admin change view
        response = self.client.get(
            reverse("admin:payment_invoice_change", args=(credit_note.pk,)),
        )

        self.assertEqual(response.status_code, 200)

        html_parser = lxml.html.HTMLParser(encoding="utf-8")
        html = lxml.html.fromstring(response.content, parser=html_parser)
        type_field = html.cssselect(".field-type .readonly")[0]

        self.assertEqual(credit_note.type, "credit_note")
        self.assertEqual(type_field.text_content(), "Credit note")

    def test_admin_invoice_display_balances(self):
        """
        Invoice admin view should display invoice balances
        (global, transactions and invoiced).
        """
        # - Login as admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # - Create an order with a related invoice
        order = factories.OrderFactory(state=enums.ORDER_STATE_VALIDATED)
        TransactionFactory(invoice__parent=order.main_invoice, total=-order.total)

        # - Now go to the invoice admin change view
        response = self.client.get(
            reverse("admin:payment_invoice_change", args=(order.main_invoice.pk,)),
        )

        self.assertEqual(response.status_code, 200)

        html_parser = lxml.html.HTMLParser(encoding="utf-8")
        html = lxml.html.fromstring(response.content, parser=html_parser)
        balance_field = html.cssselect(".field-balance .readonly")[0]
        transactions_balance_field = html.cssselect(
            ".field-transactions_balance .readonly"
        )[0]
        invoiced_balance_field = html.cssselect(".field-invoiced_balance .readonly")[0]

        null_amount_repr = "0.00"
        self.assertEqual(balance_field.text_content(), null_amount_repr)
        self.assertEqual(transactions_balance_field.text_content(), null_amount_repr)
        self.assertEqual(invoiced_balance_field.text_content(), null_amount_repr)

    def test_admin_invoice_display_invoice_children_as_link(self):
        """
        Invoice admin view should display list of
        invoice children if there are.
        """
        # - Login as admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # - Create an order with a related invoice
        order = factories.OrderFactory(state=enums.ORDER_STATE_VALIDATED)

        # - And link other invoices to this invoice
        children = InvoiceFactory.create_batch(
            2, order=order, parent=order.main_invoice, total=order.total
        )

        # - Now go to the invoice admin change view
        response = self.client.get(
            reverse("admin:payment_invoice_change", args=(order.main_invoice.pk,)),
        )

        # - Invoice are ordered by creation date

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.main_invoice.reference)

        # - Check there are links to go to invoice children admin change view
        html_parser = lxml.html.HTMLParser(encoding="utf-8")
        html = lxml.html.fromstring(response.content, parser=html_parser)
        invoice_children_field = html.cssselect(".field-children")[0]
        links = invoice_children_field.cssselect("a")

        (invoice_0, invoice_1) = children
        self.assertEqual(len(links), 2)
        self.assertEqual(
            links[0].text_content(), f"{str(invoice_0)} ({invoice_0.total})"
        )
        self.assertEqual(
            links[0].attrib["href"],
            reverse("admin:payment_invoice_change", args=(invoice_0.pk,)),
        )

        self.assertEqual(
            links[1].text_content(), f"{str(invoice_1)} ({invoice_1.total})"
        )
        self.assertEqual(
            links[1].attrib["href"],
            reverse("admin:payment_invoice_change", args=(invoice_1.pk,)),
        )

    def test_admin_invoice_display_related_transactions(self):
        """
        Invoice admin view should display transactions related to
        the invoice instance.
        """
        # - Login as admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # - Create an order with a related invoice and transaction
        order = factories.OrderFactory()
        invoice = InvoiceFactory(order=order, total=order.total)
        transaction = TransactionFactory(invoice=invoice, total=invoice.total)

        # - Now go to the invoice admin change view
        response = self.client.get(
            reverse("admin:payment_invoice_change", args=(invoice.pk,)),
        )

        # - Invoice are ordered by creation date

        self.assertEqual(response.status_code, 200)

        # - Check there are links to go to invoice children admin change view
        html_parser = lxml.html.HTMLParser(encoding="utf-8")
        html = lxml.html.fromstring(response.content, parser=html_parser)
        invoice_children_field = html.cssselect(".field-transactions")[0]
        links = invoice_children_field.cssselect("a")

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].text_content(), str(transaction))
        self.assertEqual(
            links[0].attrib["href"],
            reverse("admin:payment_transaction_change", args=(transaction.pk,)),
        )
