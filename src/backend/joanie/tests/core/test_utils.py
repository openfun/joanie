"""Test core utils."""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.test import TestCase

from joanie.core.factories import OrderFactory
from joanie.core.utils import merge_dict


class UtilsTestCase(TestCase):
    """Validate that utils in the core app work as expected."""

    def test_utils_merge_dict(self):
        """Update a deep nested dictionary with another deep nested dictionary."""
        dict_1 = {"k1": {"k11": {"a": 0, "b": 1}}}
        dict_2 = {"k1": {"k11": {"b": 10}, "k12": {"a": 3}}}
        self.assertEqual(
            merge_dict(dict_1, dict_2),
            {"k1": {"k11": {"a": 0, "b": 10}, "k12": {"a": 3}}},
        )

    def test_send_mail_with_generated_templates(self):
        """templates should have been generated on the fly and sending an email with
        these templates should work."""
        order = OrderFactory()
        template_vars = {
            "email": "test@fun-test.mooc.fr",
            "username": "Sam",
            "product": order.product,
        }
        msg_html = render_to_string("mail/html/purshase_order.html", template_vars)
        msg_plain = render_to_string("mail/text/purshase_order.txt", template_vars)
        send_mail(
            "test email sent",
            msg_plain,
            settings.EMAIL_FROM,
            [order.owner.email],
            html_message=msg_html,
            fail_silently=False,
        )
