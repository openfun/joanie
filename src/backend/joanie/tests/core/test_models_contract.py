"""Tests for the Contract Model"""
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.test import TestCase

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import factories, models


class ContractModelTestCase(TestCase):
    """
    Test case for the Contract Model
    """

    def test_models_contract_reference_datetime_not_both_set_constraint(
        self,
    ):
        """
        'signed_on' and 'submitted_for_signature_on' cannot be both set.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )
        data = {
            "order": order,
            "context": {"foo": "bar"},
            "definition_checksum": "1234",
        }
        message = "{'__all__': ['Make sure to not have both datetime fields set simultaneously.']}"
        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                **data,
                signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
                submitted_for_signature_on=datetime(
                    2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")
                ),
            )
        self.assertEqual(str(context.exception), message)

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                **data,
                signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
                submitted_for_signature_on=datetime(
                    2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")
                ),
                signature_backend_reference="wlf_dummy",
            )
        self.assertEqual(str(context.exception), message)

    def test_models_contract_reference_datetime_not_both_set_none(
        self,
    ):
        """
        'signed_on' and 'submitted_for_signature_on' can both be None.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )
        contract = factories.ContractFactory(
            order=order, signed_on=None, submitted_for_signature_on=None
        )
        contract = models.Contract.objects.get()
        self.assertIsNone(contract.signed_on)
        self.assertIsNone(contract.submitted_for_signature_on)

    def test_models_contract_reference_datetime_not_both_set_signed_on(
        self,
    ):
        """
        'signed_on' can be None and 'submitted_for_signature_on' can be set with a datetime value.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )
        factories.ContractFactory(
            order=order,
            context={"foo": "bar"},
            definition_checksum="1234",
            signed_on=None,
            submitted_for_signature_on=datetime(
                2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")
            ),
        )
        contract = models.Contract.objects.get()
        self.assertIsNone(contract.signed_on)
        self.assertIsNotNone(contract.submitted_for_signature_on)

    def test_models_contract_reference_datetime_not_both_set_submitted_for_signature_on(
        self,
    ):
        """
        'submitted_for_signature_on' can be None and 'signed_on' can be set with a datetime value.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        factories.ContractFactory(
            order=order,
            context={"foo": "bar"},
            definition_checksum="1234",
            signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=None,
        )
        contract = models.Contract.objects.get()
        self.assertIsNone(contract.submitted_for_signature_on)
        self.assertIsNotNone(contract.signed_on)

    def test_models_contract_signature_backend_reference_constraint(
        self,
    ):
        """
        If 'signature_backend_reference' is set, either 'signed_on' or 'submitted_for_signature_on'
        must also be set.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order,
                context={"foo": "bar"},
                definition_checksum="1234",
                signature_backend_reference="wlf_dummy",
                signed_on=None,
                submitted_for_signature_on=None,
            )

        message = (
            "{'__all__': "
            "['Make sure to have a date attached to the signature backend reference.']}"
        )
        self.assertEqual(str(context.exception), message)

    def test_models_contract_signature_backend_reference_signed_on(
        self,
    ):
        """
        If 'signature_backend_reference' is set, the 'signed_on' datetime can be set as long as
        the 'submitted_for_signature' datetime is not set.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        factories.ContractFactory(
            order=order,
            context={"foo": "bar"},
            definition_checksum="1234",
            signature_backend_reference="wlf_dummy",
            signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=None,
        )
        contract = models.Contract.objects.get()
        self.assertIsNotNone(contract.signature_backend_reference)
        self.assertIsNotNone(contract.signed_on)
        self.assertIsNone(contract.submitted_for_signature_on)

    def test_models_contract_signature_backend_reference_submitted_for_signature_on(
        self,
    ):
        """
        If 'signature_backend_reference' is set, the 'submitted_for_signature_on' datetime can
        be set as long as the 'signed_on' datetime is not set.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        factories.ContractFactory(
            order=order,
            context={"foo": "bar"},
            definition_checksum="1234",
            signature_backend_reference="wlf_dummy",
            signed_on=None,
            submitted_for_signature_on=datetime(
                2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")
            ),
        )
        contract = models.Contract.objects.get()
        self.assertIsNotNone(contract.signature_backend_reference)
        self.assertIsNotNone(contract.submitted_for_signature_on)
        self.assertIsNone(contract.signed_on)

    def test_models_contract_generate_complete_constraints(
        self,
    ):
        """
        If the 'definition_checksum' field is set, the 'context' field should also be set, and
        reciprocally.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )
        message = "{'__all__': ['Make sure to complete all fields when generating a contract.']}"

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order, context={"foo": "bar"}, definition_checksum=None
            )
        self.assertEqual(str(context.exception), message)

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order, context={"foo": "bar"}, definition_checksum=""
            )
        self.assertEqual(str(context.exception), message)

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order, context={}, definition_checksum="1234"
            )
        self.assertEqual(str(context.exception), message)

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(order=order, context={}, definition_checksum=None)
        self.assertEqual(str(context.exception), message)

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order, context=None, definition_checksum="1234"
            )
        self.assertEqual(str(context.exception), message)

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(order=order, context=None, definition_checksum="")
        self.assertEqual(str(context.exception), message)

    def test_models_contract_generate_complete_success_both_are_none(
        self,
    ):
        """
        'context' and 'definition_checksum' can both be None when the contract is not signed and
        not submitted for signature.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )
        factories.ContractFactory(order=order, context=None, definition_checksum=None)
        contract = models.Contract.objects.get()
        self.assertIsNone(contract.context)
        self.assertIsNone(contract.definition_checksum)

    def test_models_contract_signed_on_complete_when_context_and_definition_checksum_both_none(
        self,
    ):
        """
        'context' and 'definition_checksum' can not be left empty when the contract is signed.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        message = (
            "{'__all__': ['Make sure to complete all fields before signing contract.']}"
        )
        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order,
                context=None,
                definition_checksum=None,
                signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
            )

        self.assertEqual(str(context.exception), message)

    def test_models_contract_signed_on_complete_when_context_is_none_only(self):
        """
        'signed_on' and 'definition_checksum' have values and
        'context' is set to None.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order,
                context=None,
                definition_checksum="1234",
                signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
            )

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ["
                "'Make sure to complete all fields when generating a contract.', "
                "'Make sure to complete all fields before signing contract.']}"
            ),
        )

    def test_models_contract_signed_on_complete_when_context_and_signed_on_are_both_none(
        self,
    ):
        """
        A signed document should have a context and a definition checksum set.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        message_signed_on = (
            "{'__all__': ['Make sure to complete all fields before signing contract.']}"
        )
        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order,
                context=None,
                definition_checksum=None,
                signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
            )

        self.assertEqual(str(context.exception), message_signed_on)

    def test_models_contract_signed_on_complete_context_empty_dict_or_none_and_checksum_is_none(
        self,
    ):
        """
        'context' is an empty dictionary or 'None', and 'definition_checksum' is 'None'
        when 'signed_on' has a value.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order,
                context={},
                definition_checksum=None,
                signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
            )

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ["
                "'Make sure to complete all fields when generating a contract.',"
                " 'Make sure to complete all fields before signing contract.']}"
            ),
        )

    def test_models_contract_definition_generate_document(self):
        """
        Contract Definition 'generate document' method should generate a document.
        """
        user = factories.UserFactory()
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )
        contract = factories.ContractFactory(order=order)

        _, file_bytes = contract.definition.generate_document(order)
        document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")
        self.assertRegex(document_text, r"Student's signature")
        self.assertRegex(document_text, r"Representative's signature")
        self.assertRegex(document_text, r"Your order is delivered by the organization")
