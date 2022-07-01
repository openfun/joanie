"""ProformaInvoice admin test suite"""
from django.test import TestCase
from django.urls import reverse

import lxml.html
from djmoney.money import Money

from joanie.core import factories
from joanie.payment.factories import ProformaInvoiceFactory, TransactionFactory


class ProformaInvoiceAdminTestCase(TestCase):
    def test_admin_proforma_invoice_display_human_readable_type(self):
        """
        ProformaInvoice admin view should display
        pro forma invoice type in a human-readable manner.
        """
        # - Login as admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # - Create an order with a related pro forma invoice
        order = factories.OrderFactory()
        invoice = ProformaInvoiceFactory(order=order, total=order.total)
        credit_note = ProformaInvoiceFactory(
            order=invoice.order, parent=invoice, total=-order.total
        )

        # - Now go to the pro forma invoice admin change view
        response = self.client.get(
            reverse("admin:payment_proformainvoice_change", args=(credit_note.pk,)),
        )

        self.assertEqual(response.status_code, 200)

        html_parser = lxml.html.HTMLParser(encoding="utf-8")
        html = lxml.html.fromstring(response.content, parser=html_parser)
        type_field = html.cssselect(".field-type .readonly")[0]

        self.assertEqual(credit_note.type, "credit_note")
        self.assertEqual(type_field.text_content(), "Credit note")

    def test_admin_proforma_invoice_display_balances(self):
        """
        ProformaInvoice admin view should display pro forma invoice balances
        (global, transactions and invoiced).
        """
        # - Login as admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # - Create an order with a related pro forma invoice
        order = factories.OrderFactory()
        invoice = ProformaInvoiceFactory(order=order, total=order.total)
        ProformaInvoiceFactory(order=invoice.order, parent=invoice, total=-order.total)

        # - Now go to the pro forma invoice admin change view
        response = self.client.get(
            reverse("admin:payment_proformainvoice_change", args=(invoice.pk,)),
        )

        self.assertEqual(response.status_code, 200)

        html_parser = lxml.html.HTMLParser(encoding="utf-8")
        html = lxml.html.fromstring(response.content, parser=html_parser)
        balance_field = html.cssselect(".field-balance .readonly")[0]
        transactions_balance_field = html.cssselect(
            ".field-transactions_balance .readonly"
        )[0]
        invoiced_balance_field = html.cssselect(".field-invoiced_balance .readonly")[0]

        null_amount_repr = str(Money("0.00", order.total.currency))
        self.assertEqual(balance_field.text_content(), null_amount_repr)
        self.assertEqual(transactions_balance_field.text_content(), null_amount_repr)
        self.assertEqual(invoiced_balance_field.text_content(), null_amount_repr)

    def test_admin_proforma_invoice_display_invoice_children_as_link(self):
        """
        ProformaInvoice admin view should display list of
        pro forma invoice children if there are.
        """
        # - Login as admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # - Create an order with a related pro forma invoice
        order = factories.OrderFactory()
        invoice = ProformaInvoiceFactory(order=order, total=order.total)

        # - And link other pro forma invoices to this pro forma invoice
        children = ProformaInvoiceFactory.create_batch(
            2, order=invoice.order, parent=invoice, total=order.total
        )

        # - Now go to the pro forma invoice admin change view
        response = self.client.get(
            reverse("admin:payment_proformainvoice_change", args=(invoice.pk,)),
        )

        # - ProformaInvoice are ordered by creation date

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, invoice.reference)

        # - Check there are links to go to pro forma invoice children admin change view
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
            reverse("admin:payment_proformainvoice_change", args=(invoice_0.pk,)),
        )

        self.assertEqual(
            links[1].text_content(), f"{str(invoice_1)} ({invoice_1.total})"
        )
        self.assertEqual(
            links[1].attrib["href"],
            reverse("admin:payment_proformainvoice_change", args=(invoice_1.pk,)),
        )

    def test_admin_proforma_invoice_display_related_transactions(self):
        """
        ProformaInvoice admin view should display transactions related to
        the pro forma invoice instance.
        """
        # - Login as admin
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        # - Create an order with a related pro forma invoice and transaction
        order = factories.OrderFactory()
        invoice = ProformaInvoiceFactory(order=order, total=order.total)
        transaction = TransactionFactory(proforma_invoice=invoice, total=invoice.total)

        # - Now go to the pro forma invoice admin change view
        response = self.client.get(
            reverse("admin:payment_proformainvoice_change", args=(invoice.pk,)),
        )

        # - ProformaInvoice are ordered by creation date

        self.assertEqual(response.status_code, 200)

        # - Check there are links to go to pro forma invoice children admin change view
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
