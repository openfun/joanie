"""Test suite for batch order model."""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest import mock

from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.test import override_settings
from django.utils import timezone as django_timezone

from joanie.core import enums, factories, models
from joanie.core.utils import contract_definition
from joanie.core.utils.batch_order import validate_success_payment
from joanie.core.utils.billing_address import CompanyBillingAddress
from joanie.signature.backends import get_signature_backend
from joanie.tests.base import LoggingTestCase


# pylint: disable=too-many-public-methods
class BatchOrderModelsTestCase(LoggingTestCase):
    """Test suite for batch order model."""

    @mock.patch("joanie.core.utils.issuers.generate_document")
    def test_models_batch_order_submit_for_signature_creates_a_contract(
        self, mock_issuer_generate_document
    ):
        """
        The batch order's contract is not yet completed tag submissions values until it has
        been submitted to signature. The contract should be first generated when the batch
        order is initialized. At the end of submitting the contract we should get in
        return the invitation link to sign it.
        """
        batch_order = factories.BatchOrderFactory(
            nb_seats=2, state=enums.BATCH_ORDER_STATE_QUOTED
        )
        batch_order.quote.organization_signed_on = django_timezone.now()
        batch_order.quote.save()

        self.assertIsNotNone(batch_order.contract)
        self.assertIsNotNone(batch_order.contract.definition)
        self.assertIsNone(batch_order.contract.student_signed_on)
        self.assertIsNone(batch_order.contract.submitted_for_signature_on)
        self.assertIsNone(batch_order.contract.context)
        self.assertIsNone(batch_order.contract.signature_backend_reference)
        self.assertIsNone(batch_order.contract.definition_checksum)

        invitation_link = batch_order.submit_for_signature(user=batch_order.owner)

        batch_order.refresh_from_db()
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
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_TO_SIGN)

        context = contract_definition.generate_document_context(
            contract_definition=batch_order.offering.product.contract_definition_batch_order,
            user=batch_order.owner,
            batch_order=batch_order,
        )
        contract = factories.ContractFactory(
            definition=batch_order.offering.product.contract_definition_batch_order,
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
        batch_order.quote.organization_signed_on = django_timezone.now()
        batch_order.quote.save()

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

    def test_models_batch_order_submit_for_signature_check_contract_context_course_section(
        self,
    ):
        """
        When we call `submit_for_signature`, it will generate the context for the batch order's
        contract of the batch order. We should find the values for the course section where
        the `course_start`, `course_end`, `course_price` and `course_effort` are string type.
        """
        user = factories.UserFactory()
        factories.SiteConfigFactory(
            site=Site.objects.get_current(),
            terms_and_conditions="## Terms ",
        )
        organization = factories.OrganizationFactory()
        factories.OrganizationAddressFactory(organization=organization)
        offering = factories.OfferingFactory(
            organizations=[organization],
            product=factories.ProductFactory(
                quote_definition=factories.QuoteDefinitionFactory(),
                contract_definition_batch_order=factories.ContractDefinitionFactory(),
                title="You know nothing Jon Snow",
                target_courses=[
                    factories.CourseFactory(
                        course_runs=[
                            factories.CourseRunFactory(
                                start="2024-02-01T10:00:00+00:00",
                                end="2024-05-31T20:00:00+00:00",
                                enrollment_start="2024-02-01T12:00:00+00:00",
                                enrollment_end="2024-02-01T12:00:00+00:00",
                            )
                        ]
                    )
                ],
            ),
            course=factories.CourseFactory(
                organizations=[organization],
                effort=timedelta(hours=13, minutes=30, seconds=12),
            ),
        )
        batch_order = factories.BatchOrderFactory(
            owner=user,
            offering=offering,
            state=enums.BATCH_ORDER_STATE_TO_SIGN,
        )

        batch_order.submit_for_signature(user=user)

        contract = batch_order.contract
        course_dates = batch_order.get_equivalent_course_run_dates()

        # Course effort check
        self.assertIsInstance(batch_order.offering.course.effort, timedelta)
        self.assertIsInstance(contract.context["course"]["effort"], str)
        self.assertEqual(
            batch_order.offering.course.effort,
            timedelta(hours=13, minutes=30, seconds=12),
        )
        self.assertEqual(contract.context["course"]["effort"], "P0DT13H30M12S")

        # Course start check
        self.assertIsInstance(course_dates["start"], datetime)
        self.assertIsInstance(contract.context["course"]["start"], str)
        self.assertEqual(
            course_dates["start"], datetime(2024, 2, 1, 10, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(
            contract.context["course"]["start"], "2024-02-01T10:00:00+00:00"
        )

        # Course end check
        self.assertIsInstance(course_dates["end"], datetime)
        self.assertIsInstance(contract.context["course"]["end"], str)
        self.assertEqual(
            course_dates["end"], datetime(2024, 5, 31, 20, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(contract.context["course"]["end"], "2024-05-31T20:00:00+00:00")

        # Pricing check
        self.assertIsInstance(batch_order.total, Decimal)
        self.assertIsInstance(contract.context["course"]["price"], str)
        self.assertEqual(batch_order.total, Decimal("100.00"))
        self.assertEqual(contract.context["course"]["price"], "100.00")

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
                batch_order = factories.BatchOrderFactory(
                    state=state,
                    nb_seats=12,
                    payment_method=enums.BATCH_ORDER_WITH_CARD_PAYMENT,
                )
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

    def test_models_batch_order_generate_orders_with_quote_missing_purchase_order(self):
        """
        Orders cannot be generated if the batch order's quote has not received the purchase order.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )
        batch_order.freeze_total("100.00")

        with self.assertRaises(ValidationError) as context:
            batch_order.generate_orders()
        self.assertTrue("The batch order is not yet paid." in str(context.exception))

    def test_models_batch_order_generate_orders_with_quote_with_purchase_order_payment_method(
        self,
    ):
        """
        Orders can be generated if the batch order's quote has received the purchase order.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            nb_seats=5,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )
        batch_order.freeze_total("100.00")
        batch_order.quote.has_purchase_order = True
        batch_order.quote.save()

        batch_order.flow.update()

        batch_order.generate_orders()

        self.assertEqual(batch_order.orders.count(), 5)
        for order in batch_order.orders.all():
            self.assertIsNone(order.owner)
            self.assertEqual(order.state, enums.ORDER_STATE_TO_OWN)
            self.assertEqual(order.voucher.discount.rate, 1)

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
                address=batch_order.billing_address["address"],
                postcode=batch_order.billing_address["postcode"],
                city=batch_order.billing_address["city"],
                country=batch_order.billing_address["country"],
                first_name=batch_order.billing_address["contact_name"],
                language=batch_order.owner.language,
                last_name="",
            ),
        )

    def test_models_batch_order_create_main_invoice_should_be_none(self):
        """
        When we initialize the flow of a batch order, it should not create a main invoice,
        since we don't have yet the total price. So when we call the property `main_invoice`,
        it should return None.
        """
        batch_order = factories.BatchOrderFactory(
            nb_seats=2,
            offering__product__price=100,
            state=enums.BATCH_ORDER_STATE_DRAFT,
        )

        batch_order.init_flow()

        self.assertIsNone(batch_order.main_invoice)

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

    def test_models_batch_order_is_paid_quote_has_not_received_purchase_order(self):
        """
        When the quote related to the batch order has not received purchase order, it
        should return False and not considered as paid.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )
        batch_order.freeze_total("100.00")
        batch_order.quote.has_purchase_order = False

        self.assertFalse(batch_order.is_paid)

    def test_models_batch_order_is_paid_quote_has_received_purchase_order(self):
        """
        When the quote related to the batch order has received the purchase order, it
        should return True and considered as paid.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )
        batch_order.freeze_total("100.00")
        batch_order.quote.has_purchase_order = True

        self.assertTrue(batch_order.is_paid)

    def test_models_batch_order_is_paid_with_bank_transfer_not_confirmed(self):
        """
        When the batch order's payment method is with bank transfer and the transfer has not been
        confirmed,  `is_paid` should return False.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_PENDING,
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
        )

        self.assertFalse(batch_order.is_paid)

    def test_models_batch_order_is_paid_with_bank_transfer(self):
        """
        When the batch order's payment method is with bank transfer and the transfer has been
        confirmed, `is_paid` should return True.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_PENDING,
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
        )
        # Create the transaction and the child invoice
        validate_success_payment(batch_order)

        self.assertTrue(batch_order.is_paid)

    def test_models_batch_order_when_product_has_no_quote_definition(self):
        """
        When the product has not quote definition, it should not be possible to create
        the batch order
        """
        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
            product__quote_definition=None,
        )

        with self.assertRaises(ValidationError) as context:
            factories.BatchOrderFactory(
                owner=factories.UserFactory(), offering=offering
            )

        self.assertTrue(
            "Your product doesn't have a quote definition attached, "
            "aborting create batch order." in str(context.exception)
        )

    def test_models_batch_order_when_product_has_no_contract_definition_for_batch_order(
        self,
    ):
        """
        When the product has not contrat definition for batch order, it should not be possible
        to create the batch order
        """
        offering = factories.OfferingFactory(
            product__contract_definition_batch_order=None,
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            product__quote_definition=factories.QuoteDefinitionFactory(),
        )

        with self.assertRaises(ValidationError) as context:
            factories.BatchOrderFactory(
                owner=factories.UserFactory(), offering=offering
            )

        self.assertTrue(
            "You product doesn't have a contract definition for batch orders attached, "
            "aborting create batch order." in str(context.exception)
        )

    def test_models_batch_order_get_equivalent_course_run_dates(self):
        """
        Check that batch order's product dates are processed
        by aggregating target course runs dates as expected.
        """
        earliest_start_date = django_timezone.now() - timedelta(days=1)
        latest_end_date = django_timezone.now() + timedelta(days=2)
        latest_enrollment_start_date = django_timezone.now() - timedelta(days=2)
        earliest_enrollment_end_date = django_timezone.now() + timedelta(days=1)
        courses = (
            factories.CourseRunFactory(
                start=earliest_start_date,
                end=latest_end_date,
                enrollment_start=latest_enrollment_start_date - timedelta(days=1),
                enrollment_end=earliest_enrollment_end_date + timedelta(days=1),
            ).course,
            factories.CourseRunFactory(
                start=earliest_start_date + timedelta(days=1),
                end=latest_end_date - timedelta(days=1),
                enrollment_start=latest_enrollment_start_date,
                enrollment_end=earliest_enrollment_end_date,
            ).course,
        )
        product = factories.ProductFactory(
            target_courses=courses,
            quote_definition=factories.QuoteDefinitionFactory(),
            contract_definition_batch_order=factories.ContractDefinitionFactory(
                name=enums.PROFESSIONAL_TRAINING_AGREEMENT_UNICAMP
            ),
        )
        batch_order = factories.BatchOrderFactory(offering__product=product)

        expected_result = {
            "start": earliest_start_date,
            "end": latest_end_date,
            "enrollment_start": latest_enrollment_start_date,
            "enrollment_end": earliest_enrollment_end_date,
        }

        self.assertEqual(batch_order.get_equivalent_course_run_dates(), expected_result)
