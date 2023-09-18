"""Base Signature with Lex Persona Backend"""
import io
import json
import os
import re
import time
from logging import getLogger
from typing import Dict, List

import requests
from rest_framework import status
from rest_framework.response import Response

from joanie.core.utils import webhooks
from joanie.signature import exceptions

from ..base import BaseSignatureBackend

logger = getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class LexPersonaClient(BaseSignatureBackend):
    """
    The Signature base class.
    It contains generic methods to trigger
    the workflow process of signing a document,
    and to retrieve it once it has been signed.
    """
    configuration_keys = [
        "session_user_id",
        "token",
        "base_url",
        "profile_id",
        "consent_page_id",
        "timeout",
        "validity_period",
        "invite_period",
    ]
    configuration_defaults = {
        "timeout": 3,
        "validity_period": 60*60*24*15,
        "invite_period": 60*60*24,
    }


    def __init__(self, configuration):
        """
        Access data must be kept secret.
        Replace those values in your .env file with your
        own credentials provided by Lex Persona.
        """
        super().__init__(configuration)

        for key in self.configuration_keys:
            try:
                value = configuration.get(key, self.configuration_defaults[key])
            except KeyError:
                raise ...
            setattr(self, key, value)

    def _verify_webhook_event(self, webhook_event_id: str):
        """
        Verify if the webhook event is real.

        As we cannot trust the origin of the request, we should
        retrieve the webhook event and make sure it exists
        with this endpoint before handling the notification
        else we should not update our objects.
        """
        url = f"{self.base_url}/api/webhookEvents/{webhook_event_id}"
        response = requests.get(url, headers=self.headers, timeout=3)
        return response.ok


    def _create_workflow(self, name, description=None):
        """
        Create a workflow method : meaning that we will launch
        a process where we create a receptacle (called 'workflow')
        in order to add recipients (signers) and a document to it.

        Notes :
            - When we create the workflow, its workflowStatus is set to
            'stopped' until we update it to 'started' in order
            to launch the signature's process.

            - `self.create_payload` is a payload to prepare the
            the workflow.
        """
        url = f"{self.base_url}/api/users/{self.session_user_id}/workflows"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "name": name,
            "description": description or name,
            "steps": [
                {
                    "stepType": "signature",
                    "recipients": [],
                    "requiredRecipients": 1,
                    "validityPeriod": self.validity_period,
                    "invitePeriod": self.invite_period,
                    "maxInvites": 0,
                    "sendDownloadLink": True,
                    "allowComments": True,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": True,
                }
            ],
            "notifiedEvents": [
                "recipientRefused",
                "workflowFinished",
            ],
            "watchers": [],
        }
        response = requests.post(
            url, json=payload, headers=headers, timeout=self.timeout
        )
        if not response.ok:
            raise ...

        return response.json()["id"]

    # pylint: disable=unused-argument
    def _upload_file_to_workflow(self, file_bytes, workflow_id):
        """Upload the file to a 'workflow' that was created."""
        url = f"{self.base_url}/api/workflows/{workflow_id}/parts"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {
            "createDocuments": "true",
            "ignoreAttachments": "false",
            "signatureProfileId": self.profile_id,
            "unzip": "false",
            "pdf2pdfa": "auto",
        }
        # Create a file-like object from the bytes data
        file_obj = io.BytesIO(file_bytes)
        # Create a tuple containing the filename and file-like object
        file_data = {"file1": ("contract_definition.pdf", file_obj, "application/pdf")}
        response = requests.post(
            url, params=params, headers=headers, files=file_data, timeout=self.timeout
        )
        if not response.ok:
            raise ...

    def _start_workflow(self, workflow_id):
        """
        Start the workflow process once it has been created
        and the file has been uploaded to the workflow.
        """
        url = f"{self.base_url}/api/workflows/{workflow_id}"
        payload = {"workflowStatus": "started"}
        response = requests.patch(url, json=payload, headers=self.headers, timeout=self.timeout)
        if not response.ok or response.json().get("workflowStatus") != "started":
            raise ...

    def handle_notification(self, request):
        """
        Method triggered when a notification is sent by the signature provider.
        If the response.method is POST and the webhook event id is
        verified, then we can proceed to the webhook synchronize
        signature method.
        """
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            raise ... "Missing data from the body of the POST request"

        try:
            webhook_event_id = data["id"]
        except KeyError as error:
            logger.error("There is no ID key in the request body :%s", error)
            raise ...
  
        if not self._verify_webhook_event(webhook_event_id):
            raise ...

        workflow_id = data.get("workflowId")

        event_type = data.get("eventType")
        if event_type == "workflowFinished":
            # Set "signed_on"
            message = {"status": f"Successful document with signatures: {workflow_id}"}
            logger.info("Document with signature completed for %s", workflow_id)

        elif event_type == "recipientRefused":
            # Set contract to incident
            message = {"status": f"Refused document signature {workflow_id}"}
            logger.info("Document signature has been refused %s", workflow_id)

        else:
            raise ...

    def submit_for_signature(self, definition, file_bytes):
        """
        Wrapper to start a signature procedure with 2 signers.
        This method implies : to prepare a workflow, to upload
        a document, and start the process to sign them.
        """
        workflow_id = self._create_workflow(definition)
        self._upload_file_to_workflow(file_bytes, workflow_id)
        self._start_workflow(workflow_id)
        return workflow_id

    def get_signature_invitation_link(self, recipient_email: str, workflow_ids: list):
        """
        Create the link to go sign directly the selected documents by their workflow id.
        """
        token_jwt = self._get_jwt_token_from_invite_url(recipient_email=recipient_email)
        if not token_jwt:
            return Response(
                {"message": "Token cannot be extracted from the URL invite link"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = self._sign_specific_selection_of_workflow(
            workflow_ids=workflow_ids, token_jwt=token_jwt
        )
        return {"inviteUrlSelection": response["consentPageUrl"]}

    def refuse_signature(self, recipient_email: str, workflow_ids: list):
        """
        Refuse the invite of a workflow.
        """
        token_jwt = self._get_jwt_token_from_invite_url(recipient_email=recipient_email)
        if not token_jwt:
            return Response(
                {"message": "Token cannot be extracted from the URL invite link"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        responses = []
        for workflow_id in workflow_ids:
            url = f"{self.base_url}/api/workflows/{workflow_id}/refuse"
            headers = {
                "Authorization": f"Bearer {token_jwt}",
                "Content-Type": "application/json",
            }
            payload = {"reason": "I disagree."}
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            responses.append(response.json())
        return Response({"responses": responses}, status=status.HTTP_200_OK)

    def get_document_onetime_url(self, workflow_id: str):
        """
        Download the document of a specific workflow in PDF format.
        """
        url = f"{self.base_url}/api/workflows/{workflow_id}/downloadDocuments"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.get(url, headers=headers, timeout=3)
            if response.status_code == status.HTTP_200_OK:
                filename = "downloaded_template.pdf"
                with open(filename, "wb") as pdf_file:
                    pdf_file.write(response.content)
                    return f"{filename}"
            if response.status_code != status.HTTP_200_OK:
                raise exceptions.DownloadFileError(
                    f"Can not download document, please check your {workflow_id}"
                )
        except requests.exceptions.RequestException as exception:
            logger.error("Request Exception: %s", exception)
        return None

    def _add_recipients(self, recipients: List[Dict[str, str]]):
        """
        Add recipients to the workflow procedure that are eligible to sign the document
        which requires a signature.
        """
        recipients_data = [
            {
                "email": recipient.get("email"),
                "phoneNumber": recipient.get("phone_number"),
                "firstName": recipient.get("first_name"),
                "lastName": recipient.get("last_name"),
                "country": recipient.get("country", "FR"),
                "preferredLocale": recipient.get("preferred_locale", "fr"),
                "consentPageId": self.consent_page,
            }
            for recipient in recipients
        ]

        self.create_payload.get("steps")[0].get("recipients").extend(recipients_data)
        return self.create_payload

    def create_invitation_link_to_sign(self, recipient_email: str):
        """
        Method to create the invitation link which leads the signer
        to the consent page where the signer can see all the documents
        which require a signature.

        Note :
            - recipient_email must be a valid email that has been
            used to create a workflow as the receivers.

            - workflow_id must be the workflow that the user is
            concerned.
        """
        try:
            url = f"{self.base_url}/api/workflows/{self.workflow_id}/invite"
            payload = {"recipientEmail": recipient_email}
            response = requests.post(url, headers=self.headers, json=payload, timeout=3)
            if response.status_code == status.HTTP_404_NOT_FOUND:
                raise ValueError(
                    str(
                        f"{recipient_email} has not document registered to sign at the moment."
                    )
                )
            return response.json()
        except ValueError as exception:
            logger.error("{%s}", exception)
            return None

    def _retrieve_all_files_to_sign(self, recipient_email: str):
        """
        For organization's owners : in order to get all
        the workflows that are ongoing and the ones that
        are completed.

        The advantage of this endpoint : it will regroup
        every workflows that is linked to the recipient
        email address.

        The API filters them out according to the given
        email value.
        """
        url = f"{self.base_url}/api/workflows/"
        params = {
            "item.currentRecipientEmails": recipient_email,
        }
        response = requests.get(url, headers=self.headers, params=params, timeout=3)
        return response.json()

    def _sign_specific_selection_of_workflow(self, workflow_ids: list, token_jwt: str):
        """
        Sign a selection of document. This endpoint generates a link
        where we can go sign directly the document.
        Note :
            - payload : {"workflows" : ["workflow_id#1", "workflow_id#2"]}
        """
        headers = {
            "Authorization": f"Bearer {token_jwt}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/api/requests/"
        payload = {"workflows": workflow_ids}
        response = requests.post(url, headers=headers, json=payload, timeout=3)
        return response.json()

    def _extract_jwt_token(self, invite_url: str):
        """
        Extract the JWT token url to replace the Bearer token
        (self.token) for the 'consentPageUrl' that redirects
        to sign the document(s) directly.
        """
        token = None
        pattern = r"invite\?token=([^&]+)"
        match = re.search(pattern, invite_url)
        if match:
            token = match.group(1)
        return token

    def _get_jwt_token_from_invite_url(self, recipient_email: str):
        """
        Get JWT token for specific endpoints methods
        instead of using the current token.
        """
        try:
            response = self._create_invitation_link_to_sign(
                recipient_email=recipient_email
            )
            if response["inviteUrl"]:
                invite_url = response["inviteUrl"]
                token_jwt = self._extract_jwt_token(invite_url)
                if token_jwt is not None:
                    return token_jwt
        except TypeError as exception:
            logger.error("%s: Failed to create invitation link to sign.", exception)
        except ValueError as exception:
            logger.error(
                ("{%s}: '{%s}' is not involve in signing documents"),
                exception,
                recipient_email,
            )
        return None
