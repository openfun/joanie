"""Test suite of common methods for Base, to Dummy and Client Signature Backend."""

import random
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone as django_timezone

from joanie.core import enums, factories
from joanie.signature.backends import get_signature_backend


class BaseSignatureBackendTestCase(TestCase):
    """
    Test case of common methods from Base Signature, to Dummy and Lex Persona Signature Backend.
    """

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.base.BaseSignatureBackend"
    )
    def test_backend_signature_base_backend_get_setting_name(self):
        """
        This test verifies that the `get_setting_name` method correctly formats setting names
        with the class name and setting key.
        Example: If the class is 'BaseSignatureBackend' and the setting key is 'TOKEN',
        the expected setting name should be 'JOANIE_SIGNATURE_BASE_TOKEN'.
        """
        backend = get_signature_backend()

        token_key_setting = backend.get_setting_name("TOKEN")

        self.assertEqual(backend.name, "base")
        self.assertEqual(token_key_setting, "JOANIE_SIGNATURE_BASE_TOKEN")

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.lex_persona.LexPersonaBackend",
    )
    def test_backend_signature_client_get_setting_name_from_settings_and_retrieve_value(
        self,
    ):
        """
        This test verifies that the `get_setting_name` method correctly formats setting names
        with the class name and setting key.
        Example: If the class name is 'LexPersonaBackend' and the setting key is 'TOKEN',
        the expected setting name should be 'JOANIE_SIGNATURE_LEXPERSONA_TOKEN'.
        """
        backend = get_signature_backend()

        setting_name_token = backend.get_setting_name("TOKEN")

        self.assertEqual(backend.name, "lex_persona")
        self.assertEqual(setting_name_token, "JOANIE_SIGNATURE_LEXPERSONA_TOKEN")

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.lex_persona.LexPersonaBackend",
        JOANIE_SIGNATURE_LEXPERSONA_CONSENT_PAGE_ID="fake_cop_id",
        JOANIE_SIGNATURE_LEXPERSONA_TOKEN="fake_token_id",
    )
    def test_backend_signature_base_backend_get_setting(self):
        """
        This test verifies that the `get_setting` method correctly retrieves the value
        with a given key from the settings.
        """
        backend = get_signature_backend()

        token_key_setting = backend.get_setting("TOKEN")
        consent_page_key_setting = backend.get_setting("CONSENT_PAGE_ID")

        self.assertEqual(token_key_setting, "fake_token_id")
        self.assertEqual(consent_page_key_setting, "fake_cop_id")

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend"
    )
    def test_backend_signature_base_backend_confirm_signature(self):
        """
        This test verifies that the `confirm_signature` method updates the contract with a
        timestamps for the field `student_signed_on` or `organization_signed_on` according to
        the contract state and it should set to `None` the field `submitted_for_signature_on` if
        the contract is signed by the organization.

        Furthermore, it should update the order state.
        """
        order = factories.OrderGeneratorFactory(
            state=enums.ORDER_STATE_TO_SIGN,
            product__price=0,
        )
        contract = order.contract
        backend = get_signature_backend()

        order.submit_for_signature(order.owner)
        backend.confirm_signature(reference=contract.signature_backend_reference)

        contract.refresh_from_db()
        self.assertIsNotNone(contract.submitted_for_signature_on)
        self.assertIsNotNone(contract.student_signed_on)
        self.assertIsNone(contract.organization_signed_on)

        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        # Calling confirm_signature again should validate organization signature
        backend.confirm_signature(reference=contract.signature_backend_reference)
        contract.refresh_from_db()
        self.assertIsNone(contract.submitted_for_signature_on)
        self.assertIsNotNone(contract.student_signed_on)
        self.assertIsNotNone(contract.organization_signed_on)

    @override_settings(
        JOANIE_SIGNATURE_BACKEND=random.choice(
            [
                "joanie.signature.backends.base.BaseSignatureBackend",
                "joanie.signature.backends.dummy.DummySignatureBackend",
            ],
        ),
        JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS=60 * 60 * 24 * 15,
    )
    def test_backend_signature_base_backend_confirm_signature_but_validity_period_is_passed(
        self,
    ):
        """
        This test verifies that the `confirm_student` method does not update the contract
        if the validity period is passed. It should raise an error mentionning the validity of
        the signature is passed.
        """
        user = factories.UserFactory()
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now() - timedelta(days=16),
        )
        backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            backend.confirm_signature(reference="wfl_fake_dummy_id")

        self.assertEqual(
            str(context.exception),
            "['The contract validity date of expiration has passed.']",
        )

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend"
    )
    def test_backend_signature_base_backend_reset_contract(self):
        """
        This test verifies that the `reset_contract` method updates contract with 'None' values
        for the fields : 'context', 'definition_checksum', 'submitted_for_signature_on', and
        'signature_backend_reference'.
        """
        order = factories.OrderGeneratorFactory(
            state=enums.ORDER_STATE_SIGNING,
            product__price=0,
        )
        contract = order.contract
        backend = get_signature_backend()

        backend.reset_contract(reference=contract.signature_backend_reference)

        contract.refresh_from_db()
        self.assertIsNone(contract.student_signed_on)
        self.assertIsNone(contract.submitted_for_signature_on)
        self.assertIsNone(contract.context)
        self.assertIsNone(contract.definition_checksum)
        self.assertIsNone(contract.signature_backend_reference)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_TO_SIGN)
