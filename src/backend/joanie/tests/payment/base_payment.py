"""Common Base Payment backend test"""
from django.core import mail
from django.test import TestCase


class BasePaymentTestCase(TestCase):
    """Common method to test the Payment Backend"""

    def _check_order_validated_email_sent(self, email, username, order):
        """Shortcut to check order validated email has been sent"""
        # check email has been sent
        self.assertEqual(len(mail.outbox), 1)

        # check we send it to the right email
        self.assertEqual(mail.outbox[0].to[0], email)

        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Your order has been confirmed.", email_content)
        self.assertIn("Thank you very much for your purchase!", email_content)
        self.assertIn(order.product.title, email_content)

        # check it's the right object
        self.assertEqual(mail.outbox[0].subject, "Purchase order confirmed!")

        if username:
            self.assertIn(f"Hello {username}", email_content)
        else:
            self.assertIn("Hello", email_content)
            self.assertNotIn("None", email_content)

        # emails are generated from mjml format, test rendering of email doesn't
        # contain any trans tag, it might happen if \n are generated
        self.assertNotIn("trans ", email_content)

        # Site information are included in the email
        self.assertIn("example.com", email_content)
