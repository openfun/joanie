"""Base Signature Backend"""
import re
from logging import getLogger

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone as django_timezone

from joanie.core import models

logger = getLogger(__name__)


class BaseSignatureBackend:
    """
    This is the signature base class. First, it contains 2 generic methods responsible to retrieve
    specific key of settings and their values. Then, it contains 2 other generic methods to update
    or reset a contract.

    Finally you must implement the 4 last methods to : create a signature procedure of
    a file, get an invitation link, delete a signature procedure and handle incoming notifications.
    """

    name = "base"
    required_settings = []

    def get_setting_name(self, name):
        """
        Format setting name depending on the backend that is used.
        Example: If the class is 'BaseSignatureBackend' and the setting key is 'TOKEN',
        the expected setting name should be 'JOANIE_SIGNATURE_BASE_TOKEN'.
        """
        backend_name = re.sub(r"[^a-zA-Z]", "", self.__class__.name).upper()

        return f"JOANIE_SIGNATURE_{backend_name}_{name}"

    def get_setting(self, name):
        """
        Return the value of the setting key from the settings.
        """
        setting_name = self.get_setting_name(name)

        return getattr(settings, setting_name, None)

    def confirm_signature(self, reference):
        """
        Update the contract object when the file has been signed with the signature provider.
        We verify if the contract is still in its validity period to be sign, and if it's True
        we update the field 'signed_on' with a new timestamp.
        """
        contract = models.Contract.objects.get(signature_backend_reference=reference)

        if not contract.is_eligible_for_signing():
            logger.error(
                "Contract's validity date has passed for contract id : '%s'",
                contract.id,
            )
            raise ValidationError(
                "The contract validity date of expiration has passed."
            )

        contract.submitted_for_signature_on = None
        contract.signed_on = django_timezone.now()
        contract.save()
        logger.info("Document signature completed for the contract '%s'", contract.id)

    def reset_contract(self, reference):
        """
        Update the contract when it is refused by the signer. It resets the submission values
        of the contract.
        """
        contract = models.Contract.objects.get(signature_backend_reference=reference)
        contract.reset_submission_for_signature()
        logger.info("Document signature refused for the contract '%s'", contract.id)

    def handle_notification(self, request):
        """
        Handle incoming notification by the signature provider API.
        """
        raise NotImplementedError(
            "subclasses of BaseSignatureBackend must provide a handle_notification() method."
        )

    def submit_for_signature(self, title: str, file_bytes: bytes, order: models.Order):
        """
        Submit for signature a file with the signature provider.
        """
        raise NotImplementedError(
            "subclasses of BaseSignatureBackend must provide a submit_for_signature() method."
        )

    def get_signature_invitation_link(self, recipient_email: str, reference_ids: list):
        """
        Get an invitation link that wraps more than one document to sign at once.
        """
        raise NotImplementedError(
            "subclasses of BaseSignatureBackend must provide"
            " a get_signature_invitation_link() method."
        )

    def delete_signing_procedure(self, reference_id: str):
        """
        Delete a signing procedure registered with the contract `signature_backend_reference` value
        at the signature provider.
        """
        raise NotImplementedError(
            "subclasses of BaseSignatureBackend must provide a delete_signing_procedure() method."
        )

    def get_signed_file(self, reference_id: str):
        """
        Fetch the PDF bytes format of a contrat from the signature provider.
        """
        raise NotImplementedError(
            "subclasses of BaseSignatureBackend must provide a get_signed_file() method."
        )
