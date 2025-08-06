"""Test suite utility methods for batch orders"""

from decimal import Decimal as D
from unittest import mock

from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings

from parler.utils.context import switch_language

from joanie.core import enums, factories
from joanie.core.utils.batch_order import (
    assign_organization,
    get_active_offering_rule,
    send_mail_invitation_link,
    send_mail_vouchers,
    validate_success_payment,
)
from joanie.payment.models import Invoice, Transaction


class UtilsBatchOrderTestCase(TestCase):
    """Test suite utility methods for batch order"""

    def test_utils_batch_order_assign_organization(self):
        """
        The utility assign organization should assign the organization with least binding orders
        on the offering. It should also add the active offering rule of the offering
        on the batch order and finally it should initiate the flow. After this call, the batch
        order should have : a quote, a contract and it should be in state `quoted`.
        The main invoice and the total should still be None, since they are input later in the
        workflow process.
        """
        organization_1, organization_2 = factories.OrganizationFactory.create_batch(2)
        offering = factories.OfferingFactory(
            organizations=[organization_1, organization_2],
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
            product__price=10,
        )
        organization_1.courses.add(offering.course)
        offering_rule = factories.OfferingRuleFactory(
            nb_seats=10, course_product_relation=offering
        )

        # Create an order in completed state for organization_1
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_COMPLETED,
            product=offering.product,
            course=offering.course,
            organization=organization_1,
        )
        order.offering_rules.add(offering_rule)

        # Create the batch order
        batch_order = factories.BatchOrderFactory(
            offering=offering, nb_seats=8, state=enums.BATCH_ORDER_STATE_DRAFT
        )

        assign_organization(batch_order)

        batch_order.refresh_from_db()

        self.assertEqual(batch_order.organization, organization_2)
        self.assertEqual(batch_order.offering_rules.first(), offering_rule)
        self.assertIsNone(batch_order.main_invoice)
        self.assertIsNotNone(batch_order.contract)
        self.assertIsNotNone(batch_order.quote)
        self.assertEqual(batch_order.total, D("0.00"))
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_QUOTED)

    def test_utils_batch_order_get_active_offering_rule_not_found(self):
        """
        When no offering rule is setted for an offering, the method
        `get_active_offering_rule` should return None.
        """
        batch_order = factories.BatchOrderFactory()

        self.assertIsNone(
            get_active_offering_rule(
                offering_id=batch_order.offering.id, nb_seats=batch_order.nb_seats
            ),
        )

    def test_utils_batch_order_get_active_offering_rule(self):
        """
        The utility method `get_active_offering_rule` should return an offering rule that is
        available on the offering that corresponds to the number of seats requested by the
        batch order.
        """
        batch_order = factories.BatchOrderFactory(nb_seats=3)
        # Create 2 offering rules for the offering
        offering_rule_1 = factories.OfferingRuleFactory(
            nb_seats=1, course_product_relation=batch_order.offering
        )
        offering_rule_2 = factories.OfferingRuleFactory(
            nb_seats=3, course_product_relation=batch_order.offering
        )
        factories.OfferingRuleFactory(
            nb_seats=2, course_product_relation=batch_order.offering
        )
        # Complete the first offering rule with 2 active orders
        order = factories.OrderFactory(
            product=batch_order.offering.product,
            course=batch_order.offering.course,
            state=enums.ORDER_STATE_COMPLETED,
        )
        order.offering_rules.add(offering_rule_1)

        found_offering_rule = get_active_offering_rule(
            offering_id=batch_order.offering.id, nb_seats=batch_order.nb_seats
        )

        # The offering rule found should be the one with 3 available seats
        self.assertEqual(found_offering_rule, offering_rule_2)

    def test_utils_batch_order_get_active_offering_rule_seat_limitation_reached(self):
        """
        Should return an error if the seat limitation has been reached on all available order
        groups that have less seats than the number of seats requested by the batch order.
        """
        batch_order = factories.BatchOrderFactory(nb_seats=2)
        # Create 2 offering rules for the offering
        offering_rule = factories.OfferingRuleFactory(
            nb_seats=3, course_product_relation=batch_order.offering
        )
        # Complete the first offering rule with 2 active orders
        for _ in range(3):
            order = factories.OrderFactory(
                product=batch_order.offering.product,
                course=batch_order.offering.course,
                state=enums.ORDER_STATE_PENDING,
            )
            order.offering_rules.add(offering_rule)

        with self.assertRaises(ValueError) as context:
            get_active_offering_rule(
                offering_id=batch_order.offering.id, nb_seats=batch_order.nb_seats
            )

        self.assertTrue("Seat limitation has been reached." in str(context.exception))

    @override_settings(
        JOANIE_CATALOG_NAME="Test Catalog",
        JOANIE_CATALOG_BASE_URL="https://richie.education",
        LANGUAGES=(("fr-fr", "French"), ("en-us", "English"), ("de-de", "German")),
    )
    @mock.patch(
        "joanie.core.models.products.BatchOrder.submit_for_signature",
        return_value="https://dummmy.invitation_link.fr",
    )
    def test_utils_batch_order_send_mail_invitation_link(
        self, mock_submit_for_signature
    ):
        """
        The method `send_mail_invitation_link` should send an email with the invitation link
        to sign the contract of the batch order to the owner.
        """
        user = factories.UserFactory(
            email="johndoe@fun-test.fr",
            language="en-us",
            first_name="John",
            last_name="Doe",
        )
        batch_order = factories.BatchOrderFactory(
            owner=user,
            offering__product__title="Product 1",
        )
        batch_order.offering.product.translations.create(
            language_code="fr-fr",
            title="Produit 1",
        )
        batch_order.offering.product.save()

        invitation_link = mock_submit_for_signature()

        send_mail_invitation_link(batch_order, invitation_link)

        # check email has been sent
        self.assertEqual(len(mail.outbox), 1)

        # check we send it to the right email
        self.assertEqual(mail.outbox[0].to[0], batch_order.owner.email)

        email_content = " ".join(mail.outbox[0].body.split())

        self.assertIn("a contract awaits your signature.", email_content)
        self.assertIn(
            "To sign this document, please click the button above", email_content
        )
        self.assertIn(invitation_link, email_content)
        self.assertIn("Product 1", email_content)
        # check it's the right object
        self.assertEqual(
            mail.outbox[0].subject,
            "Product 1 - A signature is requested for your batch order.",
        )
        self.assertIn("Hello", email_content)
        self.assertNotIn("None", email_content)
        # emails are generated from mjml format, test rendering of email doesn't
        # contain any trans tag, it might happen if \n are generated
        self.assertNotIn("trans ", email_content)
        # catalog url is included in the email
        self.assertIn("https://richie.education", email_content)

        # If user has french language, the email should be in french
        with switch_language(batch_order.offering.product, "fr-fr"):
            mail.outbox.clear()
            user.language = "fr-fr"
            user.save()

            send_mail_invitation_link(batch_order, invitation_link)

            email_content = " ".join(mail.outbox[0].body.split())

            self.assertIn("Produit 1", email_content)
            self.assertIn("Bonjour", email_content)

        # If the translation does not exist, it should use the fallback language
        with switch_language(batch_order.offering.product, "de-de"):
            mail.outbox.clear()
            user.language = "de-de"
            user.save()

            send_mail_invitation_link(batch_order, invitation_link)

            email_content = " ".join(mail.outbox[0].body.split())

            self.assertIn("Product 1", email_content)
            self.assertIn("Hello", email_content)

    def test_utils_batch_order_validate_success_payment(self):
        """
        The utility method `validate_success_payment` should create the invoice and the transaction
        associated to the payment and transition de batch order to 'completed' state.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_PENDING, nb_seats=2
        )

        self.assertFalse(
            Invoice.objects.filter(
                batch_order=batch_order, parent__isnull=False
            ).exists()
        )

        validate_success_payment(batch_order)

        # Now, the child invoice and the transaction of the batch order should exist
        self.assertTrue(
            Invoice.objects.filter(
                batch_order=batch_order, parent__isnull=False
            ).exists()
        )
        self.assertTrue(
            Transaction.objects.filter(
                reference=f"bo_{batch_order.id}", total=batch_order.total
            ).exists()
        )
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)

    @override_settings(
        JOANIE_CATALOG_NAME="Test Catalog",
        JOANIE_CATALOG_BASE_URL="https://richie.education",
        LANGUAGES=(("fr-fr", "French"), ("en-us", "English"), ("de-de", "German")),
    )
    def test_utils_batch_order_send_mail_vouchers(self):
        """
        The utility method send_mail_vouchers should send the email to the batch order owner
        in his preferred language.
        """
        user = factories.UserFactory(
            email="janesmith@fun-test.fr",
            language="en-us",
            first_name="Jane",
            last_name="Smith",
        )
        offering = factories.OfferingFactory(
            product__price=10,
            product__title="Product 1",
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )
        offering.product.translations.create(
            language_code="fr-fr",
            title="Produit 1",
        )
        offering.product.save()

        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering, nb_seats=10
        )
        batch_order = factories.BatchOrderFactory(
            owner=user,
            state=enums.BATCH_ORDER_STATE_COMPLETED,
            nb_seats=2,
            offering=offering,
        )
        batch_order.offering_rules.add(offering_rule)
        batch_order.generate_orders()

        send_mail_vouchers(batch_order)

        # Verify that the orders and vouchers are created
        self.assertEqual(batch_order.orders.count(), 2)
        self.assertEqual(len(batch_order.vouchers), 2)
        # check email has been sent
        self.assertEqual(len(mail.outbox), 1)

        # check we send it to the right email
        self.assertEqual(mail.outbox[0].to[0], batch_order.owner.email)

        email_content = " ".join(mail.outbox[0].body.split())

        self.assertEqual(mail.outbox[0].subject, "Batch order payment validated!")
        self.assertIn("Hello", email_content)
        self.assertIn("Product 1", email_content)
        self.assertIn("for 2 seats", email_content)
        self.assertIn("Here are your single use vouchers", email_content)
        self.assertIn(batch_order.vouchers[0], email_content)
        self.assertIn(batch_order.vouchers[1], email_content)
        # emails are generated from mjml format, test rendering of email doesn't
        # contain any trans tag, it might happen if \n are generated
        self.assertNotIn("trans ", email_content)
        # catalog url is included in the email
        self.assertIn("https://richie.education", email_content)

        # Switch to french should use the existing translations
        with switch_language(offering.product, "fr-fr"):
            mail.outbox.clear()
            user.language = "fr-fr"
            user.save()

            send_mail_vouchers(batch_order)

            email_content = " ".join(mail.outbox[0].body.split())
            self.assertIn("Bonjour", email_content)
            self.assertIn("Produit 1", email_content)

        # When there is no translation, it should use the default language
        with switch_language(offering.product, "de-de"):
            mail.outbox.clear()
            user.language = "de-de"
            user.save()

            send_mail_vouchers(batch_order)

            email_content = " ".join(mail.outbox[0].body.split())
            self.assertIn("Hello", email_content)
            self.assertIn("Product 1", email_content)
