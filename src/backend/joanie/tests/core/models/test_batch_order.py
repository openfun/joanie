"""Test suite for batch order model."""

import json
from datetime import datetime, timedelta
from unittest import mock

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.test import override_settings
from django.utils import timezone as django_timezone

from joanie.core import enums, factories, models
from joanie.core.utils import contract_definition
from joanie.core.utils.billing_address import CompanyBillingAddress
from joanie.payment.models import Invoice
from joanie.signature.backends import get_signature_backend
from joanie.tests.base import LoggingTestCase


class BatchOrderModelsTestCase(LoggingTestCase):
    """Test suite for batch order model."""

    def test_models_batch_order_nb_seats_matches_trainees_count(self):
        """
        Ensure that the number of reserved seats (`nb_seats`) matches the number of trainees
        in the `trainees` list when saving a BatchOrder instance.
        """

        with self.assertRaises(ValidationError) as context:
            factories.BatchOrderFactory(
                nb_seats=2,
                trainees=[{"first_name": "John", "last_name": "Doe"}],
            )

        self.assertTrue(
            "The number of trainees must match the number of seats."
            in str(context.exception)
        )

    def test_models_batch_order_when_the_product_has_no_contract_definition(self):
        """
        When product does not have a contract definition, submitting to signature
        should fail and raise an error.
        """
        user = factories.UserFactory()
        offering = factories.OfferingFactory(
            product__contract_definition=None,
        )
        batch_order = factories.BatchOrderFactory(owner=user, offering=offering)

        with (
            self.assertRaises(ValidationError) as context,
            self.assertLogs("joanie") as logger,
        ):
            batch_order.submit_for_signature(user=user)

        self.assertTrue(
            "No contract definition attached to the contract's product"
            in str(context.exception)
        )
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    "No contract definition attached to the contract's product.",
                    {"batch_order": dict, "relation__product": dict},
                ),
            ],
        )

    @mock.patch("joanie.core.utils.issuers.generate_document")
    def test_models_batch_order_submit_for_signature_creates_a_contract(
        self, mock_issuer_generate_document
    ):
        """
        When the batch order does not yet have a contract, submitting to signature
        will generate one. At the end of submitting the contract we should get in
        return the invitation link to sign it.
        """
        batch_order = factories.BatchOrderFactory(
            nb_seats=2, state=enums.BATCH_ORDER_STATE_ASSIGNED
        )

        invitation_link = batch_order.submit_for_signature(user=batch_order.owner)

        batch_order.contract.refresh_from_db()
        self.assertIsNotNone(batch_order.contract)
        self.assertIsNone(batch_order.contract.student_signed_on)
        self.assertIsNotNone(batch_order.contract.submitted_for_signature_on)
        self.assertIsNotNone(batch_order.contract.context)
        self.assertIsNotNone(batch_order.contract.definition)
        self.assertIsNotNone(batch_order.contract.signature_backend_reference)
        self.assertIsNotNone(batch_order.contract.definition_checksum)
        self.assertIn("https://dummysignaturebackend.fr/?reference=", invitation_link)

        context_with_images = mock_issuer_generate_document.call_args.kwargs["context"]
        organization_logo = context_with_images["organization"]["logo"]
        self.assertIn("data:image/png;base64,", organization_logo)
        self.assertNotIn("logo_id", context_with_images["organization"])

        backend = get_signature_backend()

        backend.confirm_signature(
            reference=batch_order.contract.signature_backend_reference
        )

        batch_order.refresh_from_db()
        # We should see that the company has signed the contract
        self.assertIsNotNone(batch_order.contract.student_signed_on)

    def test_models_batch_order_submit_for_signature_a_contract_already_signed_by_buyer(
        self,
    ):
        """
        When submitting a contract that is already signed by the buyer,
        it should raise an error because we cannot submit it again.
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_SIGNING)

        with (
            self.assertRaises(PermissionDenied) as context,
            self.assertLogs("joanie") as logger,
        ):
            batch_order.submit_for_signature(user=batch_order.owner)

        self.assertEqual(
            str(context.exception),
            "Contract is already signed by the buyer, cannot resubmit.",
        )
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    "Contract is already signed by the buyer, cannot resubmit.",
                    {"contract": dict},
                ),
            ],
        )

    @override_settings(
        JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS=60 * 60 * 24 * 15,
    )
    def test_models_batch_order_submit_for_signature_same_context_but_passed_validity_period(
        self,
    ):
        """
        When the resubmitting a contract and the context has not changed but the validity
        period has passed, it should return an invitation link and update the contract fields :
        'submitted_for_signature_on', 'context', 'definition_checksum',
        and 'signature_backend_reference'.
        """
        offering = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory()
        )
        batch_order = factories.BatchOrderFactory(
            offering=offering, state=enums.BATCH_ORDER_STATE_TO_SIGN
        )

        context = contract_definition.generate_document_context(
            contract_definition=offering.product.contract_definition,
            user=batch_order.owner,
            batch_order=batch_order,
        )
        contract = factories.ContractFactory(
            definition=batch_order.offering.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="fake_test_file_hash",
            context=context,
            submitted_for_signature_on=django_timezone.now() - timedelta(days=16),
        )
        batch_order.contract = contract
        batch_order.save()

        with self.assertLogs("joanie") as logger:
            invitation_url = batch_order.submit_for_signature(user=batch_order.owner)

        batch_order.contract.refresh_from_db()
        self.assertEqual(
            contract.context, json.loads(DjangoJSONEncoder().encode(context))
        )
        self.assertIn("https://dummysignaturebackend.fr/?reference=", invitation_url)
        self.assertIn("fake_dummy_file_hash", contract.definition_checksum)
        self.assertNotEqual("wfl_fake_dummy_id", contract.signature_backend_reference)
        self.assertIsNotNone(contract.submitted_for_signature_on)
        self.assertIsNone(contract.student_signed_on)
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "WARNING",
                    "contract is not eligible for signing: signature validity period has passed",
                    {
                        "contract": dict,
                        "submitted_for_signature_on": datetime,
                        "signature_validity_period": int,
                        "valid_until": datetime,
                    },
                ),
                (
                    "INFO",
                    f"Document signature refused for the contract '{contract.id}'",
                ),
            ],
        )

    @override_settings(
        JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS=60 * 60 * 24 * 15,
    )
    def test_models_batch_order_submit_for_signature_contract_context_has_changed_and_still_valid(
        self,
    ):
        """
        When the resubmitting a contract because the context has changed and its still in the range
        of validity period, it should return an invitation link and update the contract fields :
        'submitted_for_signature_on', 'context', 'definition_checksum',
        and 'signature_backend_reference'. The newer contract can get sign by the buyer.
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_TO_SIGN)
        # Force change the product title so it modifies the contract's context when compared
        # before submitting a newer version
        batch_order.offering.product.title = "Product 123"
        batch_order.offering.product.save()

        invitation_url = batch_order.submit_for_signature(user=batch_order.owner)

        batch_order.contract.refresh_from_db()
        self.assertIn("https://dummysignaturebackend.fr/?reference=", invitation_url)
        # We should get a new signature backend reference
        self.assertNotEqual(
            "wfl_fake_dummy_123", batch_order.contract.signature_backend_reference
        )
        self.assertIn(
            "wfl_fake_dummy_", batch_order.contract.signature_backend_reference
        )
        self.assertIn("fake_dummy_file_hash", batch_order.contract.definition_checksum)
        self.assertIsNotNone(batch_order.contract.submitted_for_signature_on)
        self.assertIsNone(batch_order.contract.student_signed_on)

        backend = get_signature_backend()

        backend.confirm_signature(
            reference=batch_order.contract.signature_backend_reference
        )

        batch_order.contract.refresh_from_db()

        self.assertIsNotNone(batch_order.contract.student_signed_on)

    @mock.patch(
        "joanie.signature.backends.dummy.DummySignatureBackend.submit_for_signature",
        return_value=("mocked", "mocked"),
    )
    def test_models_batch_order_submit_for_signature(self, _mock_submit_for_signature):
        """
        When submitting the contract for signature for a batch order, it should
        set for the uploaded document title the current date, the related course code
        and the batch order pk.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED
        )

        batch_order.submit_for_signature(user=batch_order.owner)
        now = django_timezone.now()

        _mock_submit_for_signature.assert_called_once()
        # Check that the title is correctly formatted
        self.assertEqual(
            _mock_submit_for_signature.call_args[1]["title"],
            f"{now.strftime('%Y-%m-%d')}_{batch_order.offering.course.code}_{batch_order.pk}",
        )
        self.assertEqual(_mock_submit_for_signature.call_args[1]["order"], batch_order)
        self.assertIsInstance(
            _mock_submit_for_signature.call_args[1]["file_bytes"], bytes
        )

    def test_models_batch_order_in_state_assigned_without_organization(self):
        """
        A batch order cannot be in state assigned if it's not attached
        to an organization.
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_DRAFT)
        batch_order.organization = None
        batch_order.state = enums.BATCH_ORDER_STATE_ASSIGNED

        with self.assertRaises(ValidationError) as context:
            batch_order.save()

        self.assertTrue(
            "BatchOrder requires organization unless in draft or cancel states."
            in str(context.exception)
        )

    def test_models_batch_order_generate_orders(self):
        """
        Orders for a batch order can be generated when the batch order is in state
        completed only. The orders generated should not have any owners attached to
        it.
        """
        for state, _ in enums.BATCH_ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state, nb_seats=12)
                if state == enums.BATCH_ORDER_STATE_COMPLETED:
                    batch_order.generate_orders()
                    self.assertEqual(batch_order.orders.count(), 12)
                    for order in batch_order.orders.all():
                        self.assertIsNone(order.owner)
                        self.assertEqual(order.state, enums.ORDER_STATE_TO_OWN)
                        self.assertEqual(order.voucher.discount.rate, 1)
                else:
                    with self.assertRaises(ValidationError) as context:
                        batch_order.generate_orders()
                    self.assertTrue(
                        "The batch order is not yet paid." in str(context.exception)
                    )

    def test_models_batch_order_create_billing_address(self):
        """
        When we call the method to create a billing address, it should take
        the informations about the company from the batch order object.
        """
        batch_order = factories.BatchOrderFactory()

        billing_address = batch_order.create_billing_address()

        self.assertEqual(
            billing_address,
            CompanyBillingAddress(
                address=batch_order.address,
                postcode=batch_order.postcode,
                city=batch_order.city,
                country=batch_order.country,
                first_name=batch_order.owner.first_name,
                language=batch_order.owner.language,
                last_name=batch_order.owner.last_name,
            ),
        )

    def test_models_batch_order_create_main_invoice(self):
        """
        When we initialize the flow of a batch order, it creates a main invoice.
        When we call the property main_invoice, it should return the main invoice.
        """
        batch_order = factories.BatchOrderFactory(
            nb_seats=2,
            offering__product__price=100,
            state=enums.BATCH_ORDER_STATE_DRAFT,
        )

        batch_order.init_flow()

        main_invoice = Invoice.objects.get(batch_order=batch_order, parent__isnull=True)

        self.assertEqual(batch_order.main_invoice, main_invoice)

    def test_models_batch_order_property_vouchers(self):
        """
        The property vouchers should return the list of vouchers codes that are attached
        to the orders of the batch order.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_COMPLETED, nb_seats=3
        )
        batch_order.generate_orders()
        expected_vouchers = [order.voucher.code for order in batch_order.orders.all()]

        vouchers = batch_order.vouchers

        self.assertEqual(vouchers, expected_vouchers)

    def test_models_batch_order_cancel_orders(self):
        """
        When we cancel a batch order that was completed, the generated orders should be canceled
        and the voucher codes should be deleted. It's the only state where we have orders and
        vouchers available.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_COMPLETED
        )

        batch_order.generate_orders()
        # Store vouchers
        voucher_codes = batch_order.vouchers
        batch_order.flow.cancel()
        batch_order.cancel_orders()

        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_CANCELED)
        self.assertFalse(
            batch_order.orders.exclude(state=enums.ORDER_STATE_CANCELED).exists()
        )
        self.assertFalse(models.Voucher.objects.filter(code__in=voucher_codes).exists())
