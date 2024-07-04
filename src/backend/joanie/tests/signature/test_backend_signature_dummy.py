"""Test suite of the DummySignatureBackend"""

import json
import random
from io import BytesIO

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone as django_timezone

from pdfminer.high_level import extract_text as pdf_extract_text
from rest_framework.test import APIRequestFactory

from joanie.core import enums, factories
from joanie.payment.factories import InvoiceFactory
from joanie.signature.backends.base import BaseSignatureBackend
from joanie.signature.backends.dummy import DummySignatureBackend


class BaseSignatureTestCase(TestCase):
    """Common methods to test with Dummy Signature Backend."""

    def setUp(self):
        """Clears the mail outbox for each test"""
        super().setUp()
        mail.outbox.clear()

    def _check_uncomplete_signature_no_email_sent(self):
        """
        Shortcut to check if no mail has been sent
        after one invitation link.
        """
        self.assertEqual(len(mail.outbox), 0)

    def _check_signature_completed_email_sent(self, email_student):
        """
        Shortcut to check if a mail has been sent after the student has signed the file.
        """
        email_body = " ".join(mail.outbox[0].body.split())

        # check email has been sent outside
        self.assertEqual(len(mail.outbox), 1)
        # check if we've sent it to only one recipient email
        self.assertEqual(len(mail.outbox[0].to), 1)
        # check if we've sent it to the student's email
        self.assertEqual(mail.outbox[0].to[0], email_student)
        # check it's the right subject of email
        self.assertEqual(
            mail.outbox[0].subject, "A signature procedure has been completed"
        )
        self.assertIn("In order to download your file", email_body)
        self.assertIn("please follow the link :", email_body)
        # check if the download link is available in the email body
        self.assertIn("dummysignaturebackend.fr/download?", email_body)


class DummySignatureBackendTestCase(BaseSignatureTestCase):
    """Test case for the Dummy Signature Backend."""

    def test_backend_dummy_signature_name(self):
        """
        Dummy backend instance name should be 'dummy'. It should inherit from BaseSignatureBackend.
        """
        backend = DummySignatureBackend()

        self.assertIsInstance(backend, BaseSignatureBackend)
        self.assertEqual(backend.name, "dummy")

    def test_backend_dummy_signature_submit_for_signature(self):
        """
        Dummy backend instance when we submit for signature a contract.
        It should return the signature backend reference the file's hash.
        """
        backend = DummySignatureBackend()

        reference, file_hash = backend.submit_for_signature(
            "title definition 1", b"file_bytes", {}
        )

        self.assertIn("wfl_fake_dummy", reference)
        self.assertIn("fake_dummy_file_hash", file_hash)

    def test_backend_dummy_signature_get_signature_invitation_link(self):
        """
        Dummy backend instance get signature invitation link method in order to get the invitation
        to sign link in return.
        """
        backend = DummySignatureBackend()
        reference, file_hash = backend.submit_for_signature(
            "title definition 1", b"file_bytes", {}
        )
        expected_substring = (
            f"https://dummysignaturebackend.fr/?reference={reference}"
            f"&eventTarget=signed"
        )
        contract = factories.ContractFactory(
            signature_backend_reference=reference,
            definition_checksum=file_hash,
            submitted_for_signature_on=django_timezone.now(),
            context="a small context content",
        )

        response = backend.get_signature_invitation_link(
            recipient_email="student_do@example.fr",
            reference_ids=[reference],
        )

        self.assertIn(expected_substring, response)

        contract.refresh_from_db()
        self.assertIsNone(contract.student_signed_on)
        self.assertIsNotNone(contract.submitted_for_signature_on)

    def test_backend_dummy_signature_get_signature_invitation_link_with_learner_signed(
        self,
    ):
        """
        Dummy backend instance get signature invitation link method in order to get the invitation
        to sign link in return. If the learner has already signed the contract, the link should
        target the organization signature.
        """
        backend = DummySignatureBackend()
        reference, file_hash = backend.submit_for_signature(
            "title definition 1", b"file_bytes", {}
        )
        contract = factories.ContractFactory(
            signature_backend_reference=reference,
            definition_checksum=file_hash,
            submitted_for_signature_on=django_timezone.now(),
            student_signed_on=django_timezone.now(),
            context="a small context content",
        )

        response = backend.get_signature_invitation_link(
            recipient_email="student_do@example.fr",
            reference_ids=[reference],
        )

        expected_substring = (
            f"https://dummysignaturebackend.fr/?reference={reference}"
            "&eventTarget=finished"
        )
        self.assertIn(expected_substring, response)

        contract.refresh_from_db()
        self.assertIsNone(contract.organization_signed_on)
        self.assertIsNotNone(contract.student_signed_on)
        self.assertIsNotNone(contract.submitted_for_signature_on)

    def test_backend_dummy_signature_get_signature_invitation_link_for_organization(
        self,
    ):
        """
        Dummy backend instance get_signature_invitation_link method should return an
        invitation link to sign the contract.
        """
        backend = DummySignatureBackend()
        expected_substring = "https://dummysignaturebackend.fr/?reference="
        reference, file_hash = backend.submit_for_signature(
            "title definition 1", b"file_bytes", {}
        )
        contract = factories.ContractFactory(
            signature_backend_reference=reference,
            definition_checksum=file_hash,
            submitted_for_signature_on=django_timezone.now(),
            student_signed_on=django_timezone.now(),
            context="a small context content",
        )

        response = backend.get_signature_invitation_link(
            recipient_email="student_do@example.fr",
            reference_ids=[reference],
        )

        self.assertIn(expected_substring, response)

        contract.refresh_from_db()
        self.assertIsNotNone(contract.student_signed_on)
        self.assertIsNone(contract.organization_signed_on)
        self.assertIsNotNone(contract.submitted_for_signature_on)

    def test_backend_dummy_signature_get_signature_invitation_link_with_several_contracts(
        self,
    ):
        """
        Dummy backend instance get_signature_invitation_link method should return an
        invitation link to sign several contracts.
        """
        backend = DummySignatureBackend()
        expected_substring = "https://dummysignaturebackend.fr/?reference="
        signature_data = [
            backend.submit_for_signature("title definition 1", b"file_bytes", {}),
            backend.submit_for_signature("title definition 2", b"file_bytes", {}),
        ]

        contracts = []
        for reference, file_hash in signature_data:
            contract = factories.ContractFactory(
                signature_backend_reference=reference,
                definition_checksum=file_hash,
                submitted_for_signature_on=django_timezone.now(),
                context="a small context content",
            )
            contracts.append(contract)

        response = backend.get_signature_invitation_link(
            recipient_email="student_do@example.fr",
            reference_ids=[reference for reference, _ in signature_data],
        )

        self.assertIn(expected_substring, response)

        for contract in contracts:
            contract.refresh_from_db()
            self.assertIsNone(contract.student_signed_on)
            self.assertIsNotNone(contract.submitted_for_signature_on)

    def test_backend_dummy_signature_delete_signature_procedure(self):
        """
        Dummy backend instance deletes a signing procedure of an ongoing file signature procedure.
        """
        backend = DummySignatureBackend()
        reference_id, file_hash = backend.submit_for_signature(
            "definition_1", b"file_bytes", {}
        )
        contract = factories.ContractFactory(
            signature_backend_reference=reference_id,
            definition_checksum=file_hash,
            submitted_for_signature_on=django_timezone.now(),
            context="a small context content",
        )

        backend.delete_signing_procedure(reference_id=reference_id)

        contract.refresh_from_db()
        self.assertIsNone(contract.context)
        self.assertIsNone(contract.definition_checksum)
        self.assertIsNone(contract.signature_backend_reference)
        self.assertIsNone(contract.submitted_for_signature_on)

        # Check that an email has not been sent
        self._check_uncomplete_signature_no_email_sent()

    def test_backend_dummy_signature_delete_signature_procedure_that_does_not_exist(
        self,
    ):
        """
        Dummy backend instance deletes a signing procedure that does not exist raises a
        ValidationError.
        """
        backend = DummySignatureBackend()

        with self.assertRaises(ValidationError) as context:
            backend.delete_signing_procedure(reference_id="wrong_fake_dummy_id")

        self.assertEqual(
            str(context.exception), "['Cannot delete workflow wrong_fake_dummy_id.']"
        )
        # Check that an email has not been sent
        self._check_uncomplete_signature_no_email_sent()

    def test_backend_dummy_signature_handle_notification_signed_event(self):
        """
        Dummy backend instance handles notification from incoming webhook event where the type
        is "signed".
        It updates the contract for the field student_signed_on' with a timestamp value.
        """
        backend = DummySignatureBackend()
        reference, file_hash = backend.submit_for_signature(
            "definition_1", b"file_bytes", {}
        )
        contract = factories.ContractFactory(
            signature_backend_reference=reference,
            definition_checksum=file_hash,
            submitted_for_signature_on=django_timezone.now(),
            context="a small context content",
        )
        mocked_request = APIRequestFactory().post(
            reverse("webhook_signature"),
            data={
                "event_type": "signed",
                "reference": reference,
            },
            format="json",
        )
        mocked_request.data = json.loads(mocked_request.body.decode("utf-8"))

        backend.handle_notification(mocked_request)

        contract.refresh_from_db()
        self.assertIsNotNone(contract.student_signed_on)
        self.assertIsNotNone(contract.submitted_for_signature_on)

    def test_backend_dummy_signature_handle_notification_finished_event(self):
        """
        Dummy backend instance handles notification from incoming webhook event where the type
        is "finished".
        It updates the contract for the field organization_signed_on' with a timestamp value.
        """
        backend = DummySignatureBackend()
        reference, file_hash = backend.submit_for_signature(
            "definition_1", b"file_bytes", {}
        )
        contract = factories.ContractFactory(
            signature_backend_reference=reference,
            definition_checksum=file_hash,
            submitted_for_signature_on=django_timezone.now(),
            student_signed_on=django_timezone.now(),
            context="a small context content",
        )
        mocked_request = APIRequestFactory().post(
            reverse("webhook_signature"),
            data={
                "event_type": "finished",
                "reference": reference,
            },
            format="json",
        )
        mocked_request.data = json.loads(mocked_request.body.decode("utf-8"))

        backend.handle_notification(mocked_request)

        contract.refresh_from_db()
        self.assertIsNotNone(contract.student_signed_on)
        self.assertIsNotNone(contract.organization_signed_on)
        self.assertIsNone(contract.submitted_for_signature_on)

    def test_backend_dummy_signature_handle_notification_wrong_event_type(self):
        """
        Dummy backend instance handles notification from an incoming webhook event where the type
        is not supported. It should raise the fact that we do not support this type of event
        and we should not update our contract object.
        """
        backend = DummySignatureBackend()
        reference, file_hash = backend.submit_for_signature(
            "definition_1", b"file_bytes", {}
        )
        contract = factories.ContractFactory(
            signature_backend_reference=reference,
            definition_checksum=file_hash,
            submitted_for_signature_on=django_timezone.now(),
            context="a small context content",
        )
        event_type = random.choice(
            ["started", "stopped", "commented", "untracked_event"]
        )
        mocked_request = APIRequestFactory().post(
            reverse("webhook_signature"),
            data={
                "event_type": event_type,
                "reference": reference,
            },
            format="json",
        )
        mocked_request.data = json.loads(mocked_request.body.decode("utf-8"))

        with self.assertRaises(ValidationError) as context:
            backend.handle_notification(mocked_request)

        contract.refresh_from_db()
        self.assertEqual(
            str(context.exception),
            f"['The notification {event_type} is not supported.']",
        )
        self.assertIsNone(contract.student_signed_on)
        self.assertIsNotNone(contract.submitted_for_signature_on)

    def test_backend_dummy_signature_get_signed_file_with_reference_that_does_not_exist(
        self,
    ):
        """
        Dummy backend instance to get signed file method should return an exception when the
        reference id does not exist, it must raise a Validation Error.
        """
        backend = DummySignatureBackend()

        with self.assertRaises(ValidationError) as context:
            backend.get_signed_file(reference_id="wrong_fake_dummy_id")

        self.assertEqual(
            str(context.exception),
            "['Cannot download contract with reference id : wrong_fake_dummy_id.']",
        )

    def test_backend_dummy_signature_get_signed_file(
        self,
    ):
        """
        Dummy backend instance to get signed file method should return the pdf in bytes when the
        reference id exist.
        """
        contract = factories.ContractFactory(
            definition__title="Contract definition title",
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            student_signed_on=django_timezone.now(),
            organization_signed_on=django_timezone.now(),
            context="a small context",
            order__main_invoice=InvoiceFactory(
                recipient_address__address="1 Rue de L'Exemple",
                recipient_address__postcode=75000,
                recipient_address__city="Paris",
                recipient_address__country="FR",
            ),
        )
        backend = DummySignatureBackend()

        pdf_bytes = backend.get_signed_file(
            reference_id=contract.signature_backend_reference
        )

        self.assertIsInstance(pdf_bytes, bytes)

        document_text = pdf_extract_text(BytesIO(pdf_bytes)).replace("\n", "")

        self.assertIn(
            "The current contract is formed between the "
            "University and the Learner, as identified below:",
            document_text,
        )
        self.assertIn("1 Rue de L'Exemple, 75000 Paris (FR)", document_text)
        self.assertIn(contract.definition.title, document_text)

    def test_backend_dummy_update_organization_signatories_already_fully_signed(self):
        """
        Dummy backend instance should not update a signature procedure if the contract is
        fully signed.
        """
        backend = DummySignatureBackend()
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_COMPLETED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=None,
            student_signed_on=django_timezone.now(),
            organization_signed_on=django_timezone.now(),
        )
        with self.assertRaises(ValidationError) as context:
            backend.update_signatories(
                reference_id=contract.signature_backend_reference, all_signatories=False
            )

        self.assertEqual(
            str(context.exception.message),
            f"The contract {contract.id} is already fully signed",
        )

    def test_backend_dummy_update_organization_signatories(self):
        """
        It should return the contract 'reference_id' if only the organization's signature
        remains pending.
        """
        backend = DummySignatureBackend()
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_COMPLETED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=django_timezone.now(),
            student_signed_on=django_timezone.now(),
            organization_signed_on=None,
        )

        response = backend.update_signatories(
            reference_id=contract.signature_backend_reference, all_signatories=False
        )

        self.assertEqual(response, "wfl_fake_dummy_id")

    def test_backend_dummy_update_organization_signatories_order_without_contract(self):
        """
        Dummy backend instance should not update a signature procedure if the contract is
        fully signed.
        """
        backend = DummySignatureBackend()

        with self.assertRaises(ValidationError) as context:
            backend.update_signatories(
                reference_id="fake_signature_reference", all_signatories=False
            )

        self.assertEqual(
            str(context.exception.message),
            "The reference fake_signature_reference does not exist.",
        )
