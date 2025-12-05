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

from ...core.models import Contract
from .base import BaseSignatureBackend

logger = getLogger(__name__)


class DummySignatureBackend(BaseSignatureBackend):
    """A dummy signature backend to mock the behavior of a signature provider"""

    name = "dummy"
    prefix_workflow = "wfl_fake_dummy_"
    prefix_file_hash = "fake_dummy_file_hash_"
    required_settings = []

    # pylint: disable=unused-argument, no-value-for-parameter
    def submit_for_signature(
        self,
        title: str,
        file_bytes: bytes,
        order: models.Order | models.BatchOrder,
    ):
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
        Dummy method that prepares an invitation link.
        When this method is called for a single order, the invitation link includes
        the contract reference and the targeted event type. This information can be
        used by API consumers to manually trigger the notification event
        confirming the signature.
        When called with a contract from a batch order, it will automatically
        update the buyer's signature on the contract by triggering the notification
        event confirming the signature. Otherwise, if it's the organization's turn,
        the standard behavior is kept — returning the invitation link and letting
        API consumers manually trigger the notification event confirming the signature.
        """
        reference_id = reference_ids[0]
        contract = Contract.objects.get(signature_backend_reference=reference_id)
        event_target = (
            "finished" if contract.student_signed_on is not None else "signed"
        )
        # Case for batch order's contract
        if contract.batch_order and event_target == "signed":
            self.confirm_signature(reference_id)

        return (
            f"https://dummysignaturebackend.fr/?reference={reference_id}"
            f"&eventTarget={event_target}"
        )

    def delete_signing_procedure(self, reference_id: str):
        """
        Dummy method that deletes the signature procedure from a signature backend reference.
        """
        if not reference_id.startswith(self.prefix_workflow):
            raise ValidationError(f"Cannot delete workflow {reference_id}.")

        # For case of batch order, we should take away the signature of the buyer because
        # it's marked when calling `get_signature_invitation_link`
        contract = models.Contract.objects.get(signature_backend_reference=reference_id)
        if contract.batch_order:
            contract.student_signed_on = None
            contract.save()

        self.reset_contract(reference_id)

    def handle_notification(self, request):
        """
        Dummy method that handles an incoming webhook event from the signature provider.
        When the event type is "signed", it updates the field of 'student_signed_on' of the
        contract with a timestamp.
        When the event type is "finished", it updates the field of 'organization_signed_on' of the
        contract with a timestamp.
        """
        event_type = request.data.get("event_type")
        reference_id = request.data.get("reference")

        if event_type in ["signed", "finished"]:
            self.confirm_signature(reference_id)
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
        context_kwargs = {
            "contract_definition": contract.definition,
        }
        if contract.order:
            context_kwargs.update(
                {
                    "user": contract.order.owner,
                    "order": contract.order,
                }
            )
        elif contract.batch_order:
            context_kwargs.update(
                {
                    "user": contract.batch_order.owner,
                    "batch_order": contract.batch_order,
                }
            )

        return issuers.generate_document(
            name=contract.definition.name,
            context=contract_definition_utility.generate_document_context(
                **context_kwargs
            ),
        )

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
