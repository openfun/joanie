"""Common Base Payment backend test"""

from django.core import mail
from django.test import TestCase

from parler.utils.context import switch_language

from joanie.core.enums import ORDER_STATE_COMPLETED


class BasePaymentTestCase(TestCase):
    """Common method to test the Payment Backend"""

    maxDiff = None

    def _check_installment_paid_email_sent(self, email, order):
        """Shortcut to check over installment paid email has been sent"""
        # check we send it to the right email
        self.assertEqual(mail.outbox[0].to[0], email)

        # check it's the right object
        if order.state == ORDER_STATE_COMPLETED:
            self.assertIn(
                "Order completed ! The last installment of",
                mail.outbox[0].subject,
            )
        else:
            self.assertIn(
                "An installment has been successfully paid",
                mail.outbox[0].subject,
            )

        # Check body
        email_content = " ".join(mail.outbox[0].body.split())
        fullname = order.owner.get_full_name()
        self.assertIn(f"Hello {fullname}", email_content)
        self.assertIn("has been debited on the credit card", email_content)
        self.assertIn("See order details on your dashboard", email_content)
        self.assertIn(order.product.title, email_content)

        # emails are generated from mjml format, test rendering of email doesn't
        # contain any trans tag, it might happen if \n are generated
        self.assertNotIn("trans ", email_content)
        # catalog url is included in the email
        self.assertIn("https://richie.education", email_content)

    def _check_installment_refused_email_sent(self, email, order):
        """Shortcut to check over installment debit is refused email has been sent"""
        # Check we send it to the right email
        self.assertEqual(mail.outbox[0].to[0], email)

        # Check body
        email_content = " ".join(mail.outbox[0].body.split())
        fullname = order.owner.get_full_name()

        if "fr" in order.owner.language:
            self.assertRegex(
                mail.outbox[0].subject,
                "Le prélèvement d'une échéance d'un montant de .* a échoué",
            )
            self.assertIn(f"Bonjour {fullname}", email_content)
            self.assertIn(
                "Merci de régulariser le paiement en échec dès que possible depuis de",
                email_content,
            )
        else:
            self.assertIn("An installment debit has failed", mail.outbox[0].subject)
            self.assertIn(f"Hello {fullname}", email_content)
            self.assertIn(
                "Please correct the failed payment as soon as possible using",
                email_content,
            )
        # Check the product title is in the correct language
        with switch_language(order.product, order.owner.language):
            self.assertIn(order.product.title, email_content)

        # emails are generated from mjml format, test rendering of email doesn't
        # contain any trans tag, it might happen if \n are generated
        self.assertNotIn("trans ", email_content)
        # catalog url is included in the email
        self.assertIn("https://richie.education", email_content)
