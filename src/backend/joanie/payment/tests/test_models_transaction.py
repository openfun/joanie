"""Test suite for transaction model"""
from django.db.models import ProtectedError
from django.test import TestCase

from djmoney.money import Money

from joanie.core.factories import OrderFactory
from joanie.payment.factories import ProformaInvoiceFactory, TransactionFactory


class TransactionModelTestCase(TestCase):
    """
    Test case for Transaction model
    """

    def test_models_transaction_debit_string_representation(self):
        """
        If transaction amount is positive, it's string representation should
        contain debit.
        """
        transaction = TransactionFactory(total=Money("10.00", "EUR"))
        self.assertEqual(
            str(transaction),
            f"Debit transaction ({transaction.total})",
        )

    def test_models_transaction_credit_string_representation(self):
        """
        If transaction amount is negative, it's string representation should
        contain credit.
        """
        transaction = TransactionFactory(total=Money("-10.00", "EUR"))
        self.assertEqual(
            str(transaction),
            f"Credit transaction ({transaction.total})",
        )

    def test_models_transaction_protected(self):
        """
        ProformaInvoice deletion should be blocked as long as related invoice exists.
        """
        proforma_invoice = ProformaInvoiceFactory(order=OrderFactory(), total=10)
        TransactionFactory(proforma_invoice=proforma_invoice)

        with self.assertRaises(ProtectedError):
            proforma_invoice.delete()
