"""Signature Backend for Lex Persona Provider"""
import io
import json
import re
from logging import getLogger

from django.conf import settings
from django.core.exceptions import ValidationError

import requests
from rest_framework.request import Request

from joanie.core import enums, models
from joanie.signature import exceptions
from joanie.signature.backends.base import BaseSignatureBackend

logger = getLogger(__name__)


class LexPersonaBackend(BaseSignatureBackend):
    """The Lex Persona signature backend"""

    name = "lex_persona"
    required_settings = [
        "BASE_URL",
        "CONSENT_PAGE_ID",
        "SESSION_USER_ID",
        "PROFILE_ID",
        "TOKEN",
    ]

    def _prepare_recipient_data_for_student_signer(
        self, order: models.Order
    ) -> list[dict]:
        """
        Prepare recipient data of a user in order to include it in the creation payload of a
        signature procedure of a file. It returns a dictionary containing signer's information.
        """
        try:
            country = order.main_invoice.recipient_address.country.code
        except AttributeError:
            country = settings.JOANIE_DEFAULT_COUNTRY_CODE

        consent_page_id = self.get_setting("CONSENT_PAGE_ID")

        return [
            {
                "email": order.owner.email,
                "firstName": order.owner.first_name,
                # Currently, we only have the `full_name` from OpenEdx that we set in the user's
                # `first_name` in Joanie. We don't have yet the `last_name` and `first_name` that
                # are separated in our database. In order to prepare the awaited payload for the
                # signature provider, we set a dot : ".", for the `lastName` key.
                "lastName": ".",
                "country": country.upper(),
                "preferred_locale": order.owner.language.lower(),
                "consentPageId": consent_page_id,
            }
        ]

    def _prepare_recipient_data_for_organization_signer(
        self, order: models.Order
    ) -> list[dict]:
        """
        Prepare recipient data of an organization in order to include it in the creation payload
        of a signature procedure of a file. It returns a dictionary containing signer's information.
        """
        try:
            country = order.organization.country.code
        except AttributeError:
            country = settings.JOANIE_DEFAULT_COUNTRY_CODE

        consent_page_id = self.get_setting("CONSENT_PAGE_ID")
        accesses = models.OrganizationAccess.objects.filter(
            organization=order.organization, role=enums.OWNER
        )

        return [
            {
                "email": access.user.email,
                "firstName": access.user.first_name,
                "lastName": access.user.last_name,
                "country": country.upper(),
                "preferred_locale": access.user.language.lower(),
                "consentPageId": consent_page_id,
            }
            for access in accesses
        ]

    def _create_workflow(
        self,
        title: str,
        student_recipient_data: list,
        organization_recipient_data: list,
    ):
        """
        Create a workflow to initiate a signature procedure to sign a file with the signature
        provider.
        """
        timeout = settings.JOANIE_SIGNATURE_TIMEOUT
        validity_period = settings.JOANIE_SIGNATURE_VALIDITY_PERIOD

        base_url = self.get_setting("BASE_URL")
        session_user_id = self.get_setting("SESSION_USER_ID")
        token = self.get_setting("TOKEN")

        url = f"{base_url}/api/users/{session_user_id}/workflows"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "name": title,
            "description": title,
            "steps": [
                {
                    "stepType": "signature",
                    "recipients": student_recipient_data,
                    "requiredRecipients": 1,
                    "validityPeriod": validity_period,
                    "invitePeriod": None,
                    "maxInvites": 0,
                    "sendDownloadLink": True,
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                },
                {
                    "stepType": "signature",
                    "recipients": organization_recipient_data,
                    "requiredRecipients": 1,
                    "validityPeriod": validity_period,
                    "invitePeriod": None,
                    "maxInvites": 0,
                    "sendDownloadLink": True,
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                },
            ],
            "notifiedEvents": [
                "recipientRefused",
                "recipientFinished",
                "workflowFinished",
            ],
            "watchers": [],
        }
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)

        if not response.ok:
            logger.error(
                "Lex Persona: Cannot create a signature procedure, reason: %s",
                response.json(),
            )
            raise exceptions.CreateSignatureProcedureFailed(
                "Lex Persona: Cannot create a signature procedure."
            )

        return response.json()["id"]

    def _upload_file_to_workflow(self, file_bytes: bytes, reference_id: str):
        """
        Upload a file to an existing signature procedure. It returns the hash of the file generated
        by the signature provider if it was successfully uploaded, otherwise it raises an
        exception.
        """
        timeout = settings.JOANIE_SIGNATURE_TIMEOUT

        base_url = self.get_setting("BASE_URL")
        profile_id = self.get_setting("PROFILE_ID")
        token = self.get_setting("TOKEN")

        url = f"{base_url}/api/workflows/{reference_id}/parts"
        params = {
            "createDocuments": "true",
            "ignoreAttachments": "false",
            "signatureProfileId": profile_id,
            "unzip": "false",
            "pdf2pdfa": "auto",
        }
        headers = {"Authorization": f"Bearer {token}"}

        # Create a file-like object from the bytes data
        file_obj = io.BytesIO(file_bytes)
        # Create a tuple containing the filename and file-like object
        file_data = {"file1": ("contract_definition.pdf", file_obj, "application/pdf")}
        response = requests.post(
            url, params=params, headers=headers, files=file_data, timeout=timeout
        )

        if not response.ok:
            logger.error(
                "Lex Persona: Cannot upload the file to the signature provider with the signature"
                " reference, reason: %s",
                response.json(),
            )
            raise exceptions.UploadFileFailed(
                "Lex Persona: Cannot upload the file to the signature provider "
                "with the signature reference."
            )

        return response.json().get("parts")[0].get("hash")

    def _start_procedure(self, reference_id: str):
        """
        Start a signature procedure that exists by updating its status to "started".
        """
        timeout = settings.JOANIE_SIGNATURE_TIMEOUT

        base_url = self.get_setting("BASE_URL")
        token = self.get_setting("TOKEN")

        url = f"{base_url}/api/workflows/{reference_id}"
        payload = {"workflowStatus": "started"}
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.patch(url, json=payload, headers=headers, timeout=timeout)

        if not response.ok or response.json().get("workflowStatus") != "started":
            logger.error(
                "Lex Persona: Cannot start the signature procedure with signature reference, "
                "reason: %s",
                response.json(),
            )
            raise exceptions.StartSignatureProcedureFailed(
                "Lex Persona: Cannot start the signature procedure with signature reference"
            )

    def _get_jwt_token_from_invitation_link(
        self, recipient_email: str, reference_id: str
    ):
        """
        Convenience method that prepares the invitation URL in order to extract the JWT
        (JSON Web Token) from the invite URL. When the request to retrieve the invite URL
        fails, it raises an exception. Otherwise, it returns the string of the JWT token.
        """
        response = self._create_invitation_link_to_sign(
            recipient_email=recipient_email, reference_id=reference_id
        )
        if not response.ok:
            logger.error(
                "Lex Persona: Cannot create invitation link for %s, reason: %s",
                recipient_email,
                response.json(),
            )
            raise exceptions.InvitationSignatureFailed(
                f"Lex Persona: Cannot create invitation link for {recipient_email}"
            )

        invitation_link = response.json().get("inviteUrl")
        token_jwt = self._extract_jwt_token_from_invitation_link(invitation_link)

        return token_jwt

    def _extract_jwt_token_from_invitation_link(self, invitation_link: str):
        """
        Extract a JWT (JSON Web Token) from an invite URL. This method retrieves the invite
        URL from the response of 'create_invitation_link_to_sign' and attempts to extract a
        JWT token from it. If a valid JWT token is found in the URL, it is returned as a string.
        Otherwise, if no token is found, it returns None.
        """
        token = None
        pattern = r"invite\?token=(?P<token>[^&]+)"

        match = re.search(pattern, invitation_link)

        if match is None:
            logger.error(
                "Cannot extract JWT Token from the invite url of the signature provider"
            )
            raise ValueError(
                "Cannot extract JWT Token from the invite url of the signature provider"
            )

        token = match.group("token")
        return token

    def _create_invitation_link_to_sign(self, recipient_email: str, reference_id: str):
        """
        Retrieve the invitation link to sign a file through the consent page.
        This method is mainly used to get the invite URL to extract the JWT (JSON Web
        Token) in order to use for the endpoint '_sign_selection_of_workflow'.
        """
        timeout = settings.JOANIE_SIGNATURE_TIMEOUT

        base_url = self.get_setting("BASE_URL")
        token = self.get_setting("TOKEN")

        url = f"{base_url}/api/workflows/{reference_id}/invite"
        payload = {"recipientEmail": recipient_email}
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if not response.ok:
            logger.error(
                "Lex Persona: %s has no documents registered to sign at the moment, reason: %s",
                recipient_email,
                response.json(),
            )
            raise exceptions.InvitationSignatureFailed(
                f"Lex Persona: {recipient_email} has no documents "
                "registered to sign at the moment.",
            )

        return response

    def _sign_specific_selection_of_references(
        self, reference_ids: list, token_jwt: str
    ):
        """
        Sign specific selection of signature references using a JWT token. This method takes a list
        of reference IDs and a JWT token as input, and it uses the token to authenticate and
        authorize the signing of specific references.
        """
        timeout = settings.JOANIE_SIGNATURE_TIMEOUT

        base_url = self.get_setting("BASE_URL")

        url = f"{base_url}/api/requests/"
        payload = {"workflows": reference_ids}
        headers = {
            "Authorization": f"Bearer {token_jwt}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, headers=headers, json=payload, timeout=timeout)

        if not response.ok:
            logger.error(
                "Lex Persona: Cannot get invitation link to sign the file from the signature"
                " provider, reason: %s",
                response.json(),
            )
            raise exceptions.InvitationSignatureFailed(
                "Lex Persona: Cannot get invitation link to sign the file "
                "from the signature provider."
            )

        return response

    def _verify_webhook_event(self, webhook_event_id: str):
        """
        This method verifies a webhook event by making a request to the signature provider's
        API with the provided `webhook_event_id`. If the webhook event has been verified, we return
        the response. Otherwise, we raise an error.
        """
        timeout = settings.JOANIE_SIGNATURE_TIMEOUT

        base_url = self.get_setting("BASE_URL")
        token = self.get_setting("TOKEN")

        url = f"{base_url}/api/webhookEvents/{webhook_event_id}"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers, timeout=timeout)
        if not response.ok:
            logger.error(
                "Lex Persona: Unable to verify the webhook event with the signature "
                "provider, reason: %s",
                response.json(),
            )
            raise ValidationError(
                "Lex Persona: Unable to verify the webhook event with the signature provider."
            )

        return response.json()

    def submit_for_signature(self, title: str, file_bytes: bytes, order: models.Order):
        """
        Convenience method that wraps the signature procedure creation, file upload, and start
        the signing procedure.
        It returns the signature backend reference and the hash of the file from the signature
        provider.
        """
        student_recipient_data = self._prepare_recipient_data_for_student_signer(order)
        organization_recipient_data = (
            self._prepare_recipient_data_for_organization_signer(order)
        )
        reference_id = self._create_workflow(
            title, student_recipient_data, organization_recipient_data
        )
        file_hash = self._upload_file_to_workflow(file_bytes, reference_id)
        self._start_procedure(reference_id=reference_id)

        return reference_id, file_hash

    def handle_notification(self, request: Request):
        """
        Handle notification for incoming webhook events from the signature provider.
        First, we verify the authenticity of the webhook event, then its event type, and finally if
        the signature procedure has not passed its validity period.
        Once those conditions are met, we can proceed in updating the contract attached to the
        signature backend reference of the incoming event.
        If the validity period has passed or has been refused by the signer, we reset the contract.
        If the event type is not tracked, we raise a error.
        """
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as error:
            logger.error("The JSON body of the request is malformed")
            raise ValidationError(
                "The JSON body of the request is malformed"
            ) from error

        try:
            webhook_event_id = data["id"]
        except KeyError as error:
            logger.error("There is no ID key in the request body")
            raise KeyError(
                "Missing the key id to retrieve from the webhook event data"
            ) from error

        try:
            trusted_event_signature_provider = self._verify_webhook_event(
                webhook_event_id
            )
        except ValidationError as error:
            logger.error("The webhook event cannot be trusted : %s", webhook_event_id)
            raise ValidationError(
                "Lex Persona: Unable to verify the webhook event with the signature provider."
            ) from error

        reference_id = trusted_event_signature_provider.get("workflowId")
        event_type = trusted_event_signature_provider.get("eventType")
        if event_type == "workflowFinished":
            self.confirm_organization_signature(reference_id)
        elif event_type == "recipientFinished":
            self.confirm_student_signature(reference_id)
        elif event_type == "recipientRefused":
            self.reset_contract(reference_id)
        else:
            logger.error("'%s' is not an event type that we handle.")
            raise ValidationError(
                f"The notification {event_type} is not supported.",
            )

    def get_signature_invitation_link(self, recipient_email: str, reference_ids: list):
        """
        Retrieve the signature invitation link for one or more signature processes for a specified
        recipient email. It returns a one-time link to sign the selection of files by their
        signature backend references.
        """
        token_jwt = self._get_jwt_token_from_invitation_link(
            recipient_email=recipient_email, reference_id=reference_ids[0]
        )
        response = self._sign_specific_selection_of_references(
            reference_ids=reference_ids, token_jwt=token_jwt
        )

        if not response.ok:
            logger.error(
                "Lex Persona: Cannot get invitation link to sign the file from the signature"
                " provider, reason: %s",
                response.json(),
            )
            raise exceptions.InvitationSignatureFailed(
                "Lex Persona: Cannot get invitation link to sign the file from "
                "the signature provider."
            )

        return response.json().get("consentPageUrl")

    def delete_signing_procedure(self, reference_id: str):
        """
        Delete a signing procedure associated of a given signature backend reference.

        Here are some cases where you will use this method, for example :
        - if the file's context has been updated since the last submission
        - if the signing procedure has passed its validity period.

        The goal is to avoid the user to sign a file that is not valid anymore
        and to delete the signature procedure on the provider's side.
        """
        timeout = settings.JOANIE_SIGNATURE_TIMEOUT

        base_url = self.get_setting("BASE_URL")
        token = self.get_setting("TOKEN")

        url = f"{base_url}/api/workflows/{reference_id}"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.delete(url, headers=headers, timeout=timeout)

        if not response.ok:
            logger.error(
                "Lex Persona: Unable to delete the signature procedure"
                " the reference does not exist %s, reason: %s",
                reference_id,
                response.json(),
            )
            raise exceptions.DeleteSignatureProcedureFailed(
                "Lex Persona: Unable to delete the signature procedure"
                f" the reference does not exist {reference_id}"
            )

        return response.json()

    def get_signed_file(self, reference_id: str) -> bytes:
        """
        Return the file in PDF bytes format once it has been completely signed Lex Persona.
        """
        timeout = settings.JOANIE_SIGNATURE_TIMEOUT

        base_url = self.get_setting("BASE_URL")
        token = self.get_setting("TOKEN")

        url = f"{base_url}/api/workflows/{reference_id}/downloadDocuments"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers, timeout=timeout)

        if not response.ok:
            logger.error(
                "Lex Persona: There is no document with the specified reference : %s, reason : %s",
                reference_id,
                response.json(),
            )
            raise ValidationError(
                f"Lex Persona: The specified reference can not be found : {reference_id}."
            )

        return response.content
