"""Dummy Signature Backend"""

import smtplib
from logging import getLogger
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail

from joanie.core import models
from joanie.core.utils import contract_definition as contract_definition_utility
from joanie.core.utils import issuers

from .base import BaseSignatureBackend

logger = getLogger(__name__)


class DummySignatureBackend(BaseSignatureBackend):
    """A dummy signature backend to mock the behavior of a signature provider"""

    name = "dummy"
    prefix_workflow = "wfl_fake_dummy_"
    prefix_file_hash = "fake_dummy_file_hash_"
    required_settings = []

    # pylint: disable=unused-argument, no-value-for-parameter
    def submit_for_signature(self, title: str, file_bytes: bytes, order: models.Order):
        """
        Dummy method that creates a signature procedure with a fake file to be signed.
        It returns a dummy signature backend reference, and a dummy file hash.
        """
        fake_id = uuid4()
        dummy_reference_id = f"{self.prefix_workflow}{fake_id}"
        dummy_file_hash = f"{self.prefix_file_hash}{fake_id}"

        return dummy_reference_id, dummy_file_hash

    def get_signature_invitation_link(self, recipient_email: str, reference_ids: list):
        """
        Dummy method that prepares an invitation link, and it triggers an email notifying that the
        file is available to download to the signer by email.
        """

        contracts = models.Contract.objects.filter(
            signature_backend_reference__in=reference_ids
        ).only("organization_signed_on", "signature_backend_reference")

        for contract in contracts:
            event_type = "finished" if contract.student_signed_on else "signed"
            reference = contract.signature_backend_reference
            self.handle_notification({"event_type": event_type, "reference": reference})

            self._send_email(recipient_email=recipient_email, reference_id=reference)

        return f"https://dummysignaturebackend.fr/?requestToken={reference_ids[0]}#requestId=req"

    def delete_signing_procedure(self, reference_id: str):
        """
        Dummy method that deletes the signature procedure from a signature backend reference.
        """
        if not reference_id.startswith(self.prefix_workflow):
            raise ValidationError(f"Cannot delete workflow {reference_id}.")

        self.reset_contract(reference_id)

    def handle_notification(self, request):
        """
        Dummy method that handles an incoming webhook event from the signature provider.
        When the event type is "signed", it updates the field of 'student_signed_on' of the
        contract with a timestamp.
        When the event type is "finished", it updates the field of 'organization_signed_on' of the
        contract with a timestamp.
        """
        event_type = request.get("event_type")
        reference_id = request.get("reference")

        if event_type == "signed":
            self.confirm_student_signature(reference_id)
        elif event_type == "finished":
            self.confirm_organization_signature(reference_id)
        else:
            logger.error("'%s' is not an event type that we handle.")
            raise ValidationError(
                f"The notification {event_type} is not supported.",
            )

    def _send_email(self, recipient_email: str, reference_id: str):
        """
        Dummy method that sends an email with a download link once the document has been
        signed by the required signer.
        """
        link = (
            "https://dummysignaturebackend.fr/download?url=https://dummysignaturebackend"
            f".fr/{reference_id}?token=fake_dummy_token"
        )

        try:
            send_mail(
                subject="A signature procedure has been completed",
                message=f"In order to download your file, please follow the link : {link}",
                from_email=settings.EMAIL_FROM,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
        except smtplib.SMTPException as exception:
            logger.error("Failed to send mail: '%s'", exception)

        logger.info(
            "Mail for '%s' is sent from Dummy Signature Backend",
            reference_id,
        )

    def get_signed_file(self, reference_id: str) -> bytes:
        """
        Dummy method that returns a contract in PDF bytes if the reference exists.
        """
        if not reference_id.startswith(self.prefix_workflow):
            raise ValidationError(
                f"Cannot download contract with reference id : {reference_id}."
            )

        contract = models.Contract.objects.get(signature_backend_reference=reference_id)
        file_bytes = issuers.generate_document(
            name=contract.definition.name,
            context=contract_definition_utility.generate_document_context(
                contract_definition=contract.definition,
                user=contract.order.owner,
                order=contract.order,
            ),
        )

        return file_bytes

    def update_signatories(self, reference_id: str, all_signatories: bool) -> str:
        """
        Dummy method that verifies if the order is not fully signed yet, else it returns the
        signature backend reference that has been updated.
        """
        if not reference_id.startswith(self.prefix_workflow):
            raise ValidationError(f"The reference {reference_id} does not exist.")

        contract = models.Contract.objects.get(
            signature_backend_reference=reference_id,
        )
        if contract.is_fully_signed:
            raise ValidationError(f"The contract {contract.id} is already fully signed")

        return contract.signature_backend_reference
