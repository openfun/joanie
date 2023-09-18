"""Common Base Signature backend test."""
from django.core import mail
from django.test import TestCase


class BaseSignatureTestCase(TestCase):
    """Common method to test the Signature Backend."""

    def setUp(self):
        """Clears the mail outbox for each test"""
        mail.outbox.clear()

    def _check_uncomplete_signature_no_email_sent(self):
        """
        Shortcut to check if no mail has been sent
        after one invitation link.
        """
        self.assertEqual(len(mail.outbox), 0)

    def _check_signature_completed_email_sent(self, email_student, workflow_id):
        """
        Shortcut to check if a mail has been sent after the student has signed the document.
        """
        # check email has been sent outside
        self.assertEqual(len(mail.outbox), 1)
        # check if we've sent it to only one recipient email
        self.assertEqual(len(mail.outbox[0].to), 1)
        # check if we've sent it to the student's email
        self.assertEqual(mail.outbox[0].to[0], email_student)
        # check it's the right subject of email
        self.assertEqual(
            mail.outbox[0].subject, "A document signature procedure has been completed"
        )
        email_body = " ".join(mail.outbox[0].body.split())
        self.assertIn("In order to download your documents", email_body)
        self.assertIn("please follow the link below :", email_body)
        # check if the download link is available in the email body
        self.assertIn("dummysignaturebackend.fr/download?", email_body)
        self.assertIn(workflow_id, email_body)
