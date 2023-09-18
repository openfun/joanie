"""Dummy Signature Backend"""
import logging
import secrets
import smtplib
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

from .base import BaseSignatureBackend

logger = logging.getLogger(__name__)


class DummySignatureBackend(BaseSignatureBackend):
    """Dummy Signature Backend to mock behavior of a provider using cache."""

    name = "dummy"
    required_recipients = 1
    workflow_id = str()

    def handle_notification(self, request):
        """
        Dummy method that handles an incoming event from the signature provider.
        If the event type is authorized and the webhook event ID is registered in the cache.
        Else, it returns a message indicating that the event cannot be verified.

        The method supports the following event types:

        - Signed document :
            {
                "eventType": "workflowFinished",
                "id": "wbe_dummy_test_xyz",
                "workflowId": "wlf_dummy_test_{contract_id}"
            }

        This event indicates that the entire workflow has been completed,
        and the required recipient has signed the document.
        The workflowStatus of this procedure will be set at "finished"

        - Refusal of the invitation :
            {
                "eventType": "recipientRefused",
                "id": "wbe_dummy_test_xzy",
                "workflowId": "wlf_dummy_test_{contract_id}"
            }
        This event indicates that the entire workflow has been aborted.
        The workflowStatus of this procedure will be set at "stopped"
        """
        event_type = request.get("eventType")
        webhook_event_id = request.get("id")
        workflow_id = request.get("workflowId")
        workflow_data = cache.get(self.workflow_id)
        workflow_data_item, _ = self._get_item_from_cache(workflow_id, workflow_data)

        if not workflow_data_item:
            return f"Workflow can not be found {workflow_id}"
        if workflow_data_item:
            event_messages = {
                "workflowFinished": "All parties have signed the document",
                "recipientRefused": "Document Signature has been aborted",
            }
            if event_type in event_messages:
                if webhook_event_id in workflow_data_item["webhook_events_id"]:
                    return event_messages[event_type]

        return "Failed, this event can not be verified"

    def upload_file(self, *args, **kwargs):
        """
        Dummy method to create a workflow in order to upload a file,
        add recipients of signers and start the procedure.
        """
        contract_id = uuid.uuid4()
        self.workflow_id = self._create_workflow_id(contract_id)
        signers_info = {
            "items": [
                {
                    "contract_id": str(contract_id),
                    "id": str(self.workflow_id),
                    "recipients": {
                        "student_do@example.fr": False,
                    },
                    "workflowStatus": "started",
                    "parts": "template.pdf",
                    "provider": str(self.name),
                    "requiredRecipients": self.required_recipients,
                    "webhook_events_id": [],
                    "webhook_events_detail": [],
                },
            ],
        }
        cache.set(self.workflow_id, signers_info)

        return signers_info

    def create_invitation_link(self, recipient_email: str, *args, **kwargs):
        """
        Dummy method that prepares invitation link for a recipient email.
        If a workflow has reached the end of the procedure, it triggers a mail
        with the download link of the signed document.
        It triggers a webhook event in which we handle into cache data.
        """
        invite_link = ""
        workflow_data = cache.get(self.workflow_id)
        workflow_item_id = kwargs["workflow_id"]
        workflow_data_item, index = self._get_item_from_cache(
            workflow_item_id, workflow_data
        )
        if not workflow_data_item:
            return f"Workflow can not be found : '{workflow_item_id}'"

        if recipient_email not in workflow_data_item["recipients"]:
            raise ValueError(
                f"Your recipient email {recipient_email} is not correct, try again"
            )

        workflow_data_item["recipients"][recipient_email] = True
        self._update_cache_data(index, workflow_data_item)
        workflow_data = self._get_cache_data()
        invite_link = self._prepare_invite_link()
        mock_webhook_event = self._send_post_webhook_event(
            workflow_id=workflow_item_id,
            refused=False,
            finished=False,
        )
        self.handle_notification(mock_webhook_event)

        if self._check_required_recipient_signature(workflow_data_item["recipients"]):
            mock_webhook_event = self._send_post_webhook_event(
                workflow_id=workflow_item_id,
                refused=False,
                finished=True,
            )
            self.handle_notification(mock_webhook_event)
            self._send_mail_document_signatures_completed(workflow_item_id)

        return invite_link

    def get_signature_invitation_link(self, recipient_email: str, workflow_ids: list):
        """
        Prepare a specific invitation link that wraps more than one document to sign at once.
        For the dummy version, we will return a link that aims to mock the fact of signing all
        the documents into the list of workflow ids.
        """
        token = secrets.token_urlsafe()
        mock_request_invitation_link = (
            f"https://dummysignaturebackend.fr/?requestToken={token}#requestId"
        )

        for workflow_id in workflow_ids:
            self.create_invitation_link(
                recipient_email=recipient_email, **{"workflow_id": workflow_id}
            )
        return {"inviteUrlSelection": mock_request_invitation_link}

    def refuse_signature(self, recipient_email: str, workflow_ids: list):
        """
        Refuse the invitation to sign a document.
        """
        workflow_failed_to_refused = []
        workflow_succeed_to_refused = []
        workflow_data = self._get_cache_data()
        for workflow_id in workflow_ids:
            item, index = self._get_item_from_cache(workflow_id, workflow_data)
            if item is not None:
                item["workflowStatus"] = "stopped"
                self._update_cache_data(index, item)
                self._send_post_webhook_event(
                    workflow_id=workflow_id, refused=True, finished=False
                )
                workflow_succeed_to_refused.append(workflow_id)
                logger.info(
                    "'%s' has been stopped by : '%s'", workflow_id, recipient_email
                )
            else:
                workflow_failed_to_refused.append(workflow_id)
                logger.info("'%s' not found in workflow data.", workflow_id)
        data = {
            "success": workflow_succeed_to_refused,
            "fail": workflow_failed_to_refused,
        }
        return data

    def get_document_onetime_url(self, workflow_id: str):
        """
        Download the document that is signed by the minimum required recipient
        The 'workflowStatus' has to be 'finished'
        """
        workflow_data = self._get_cache_data()
        workflow_data_item, _ = self._get_item_from_cache(workflow_id, workflow_data)

        if not workflow_data_item:
            return f"Workflow can not be found {workflow_id}"

        status = workflow_data_item["workflowStatus"]
        if status == "finished":
            token = secrets.token_urlsafe()
            download_link = {
                "downloadUrl": "https://dummysignaturebackend.fr/download?url=https://dummy"
                f"signaturebackend.fr/{workflow_id}?token={token}"
            }
            return download_link
        if status == "stopped":
            return (
                f"'{workflow_id}' has been refused, its current status is : '{status}'"
            )
        # if status is "started"
        return (
            f"'{workflow_id}' is not yet finished, its current status is : '{status}'"
        )

    def _create_workflow_id(self, contract_id):
        """Simulate the creation of a workflow id."""
        return f"wlf_dummy_test_{contract_id}"

    def _get_cache_data(self):
        """
        Retrieve cache data from dummy backend
        """
        return cache.get(self.workflow_id)

    def _update_cache_data(self, index, item):
        """
        Update cache data for dummy backend according to the key index of an item.
        """
        workflow_data = cache.get(self.workflow_id)
        del workflow_data["items"][index]
        workflow_data["items"].insert(index, item)
        cache.set(self.workflow_id, workflow_data)

    def _get_item_from_cache(self, workflow_item_id: str, workflow_data: dict):
        """
        Get the appropriate item from cache with the workflow id
        """
        items = workflow_data.get("items", [])
        matching_items = [item for item in items if item.get("id") == workflow_item_id]

        if matching_items == []:
            return None, None

        workflow_data_item = matching_items[0]
        index = next(
            (
                idx
                for idx, item in enumerate(items)
                if item.get("id") == workflow_item_id
            ),
            -1,
        )
        return workflow_data_item, index

    def _add_a_workflow_to_items(self):
        """
        Adds a new item into cache in 'items' key. We simulate when there are many
        documents to be signed on different procedures.
        """
        contract_id = uuid.uuid4()
        second_workflow_id = self._create_workflow_id(contract_id)
        second_workflow = {
            "contract_id": str(contract_id),
            "id": str(second_workflow_id),
            "recipients": {
                "student_do@example.fr": False,
            },
            "workflowStatus": "started",
            "parts": "template_2.pdf",
            "provider": str(self.name),
            "requiredRecipients": self.required_recipients,
            "webhook_events_id": [],
            "webhook_events_detail": [],
        }

        # Update the cache by adding it to items
        workflow_data = cache.get(self.workflow_id)
        workflow_data["items"].append(second_workflow)
        workflow_data = cache.set(self.workflow_id, workflow_data)
        workflow_data = cache.get(self.workflow_id)

        return workflow_data

    def _check_required_recipient_signature(self, recipients_dict: dict) -> bool:
        """Verify if at least two recipients have signed the document."""
        signed_count = sum(1 for value in recipients_dict.values() if value)
        return signed_count >= self.required_recipients

    def _prepare_invite_link(self):
        """Generate token and prepare the invitation link."""
        token = secrets.token_urlsafe()
        response = {
            "inviteUrl": f"https://dummysignaturebackend.fr/invite?token={token}"
        }
        return response

    def _send_post_webhook_event(self, workflow_id: str, refused=False, finished=False):
        """
        Prepare the webhook event data in order to mock the behavior
        of the signature provider API when events occur on the document to get signed.
        """
        workflow_data = self._get_cache_data()
        item, index = self._get_item_from_cache(workflow_id, workflow_data)

        dummy_webhook = {"id": None, "workflowId": workflow_id, "eventType": None}

        if not item:
            dummy_webhook[
                "eventType"
            ] = f"Workflow can not be found with : '{workflow_id}'"
            return dummy_webhook

        if item["workflowStatus"] == "finished":
            dummy_webhook["eventType"] = f"Workflow is finished already {workflow_id}"
            return dummy_webhook

        random_id = uuid.uuid4()
        webhook_event_id = f"wbe_dummy_test_{random_id}"
        dummy_webhook["id"] = webhook_event_id
        item["webhook_events_id"].append(webhook_event_id)

        self._update_cache_data(index, item)
        update_workflow_data = self._get_cache_data()
        updated_item, index = self._get_item_from_cache(
            workflow_id, update_workflow_data
        )

        if (
            len(updated_item["webhook_events_id"]) >= self.required_recipients
            or finished
        ):
            dummy_webhook["eventType"] = "workflowFinished"
            updated_item["workflowStatus"] = "finished"

        if refused:
            dummy_webhook["eventType"] = "recipientRefused"
            updated_item["workflowStatus"] = "stopped"

        updated_item["webhook_events_detail"].append(dummy_webhook)

        self._update_cache_data(index, updated_item)

        return dummy_webhook

    def _send_mail_document_signatures_completed(self, workflow_id: str):
        """
        When the process is completed (according to required recipient value),
        we will send an email with a download link.
        """
        workflow_data = self._get_cache_data()
        workflow_data_item, _ = self._get_item_from_cache(workflow_id, workflow_data)
        try:
            recipients = [
                email
                for email, value in workflow_data_item["recipients"].items()
                if value
            ]
            token = secrets.token_urlsafe()
            link = (
                "https://dummysignaturebackend.fr/download?url=https://dummysignaturebackend"
                f".fr/{workflow_id}?token={token}"
            )
            message = f"In order to download your documents, please follow the link below : {link}"
            send_mail(
                subject="A document signature procedure has been completed",
                message=message,
                from_email=settings.EMAIL_FROM,
                recipient_list=recipients,
                fail_silently=False,
            )
            logger.info(
                "Mail for '%s' is sent to %s from dummy signature",
                workflow_id,
                recipients,
            )
        except smtplib.SMTPException as exception:
            logger.error("Failed to send mail: '%s'", exception)
        except TypeError as exception:
            logger.error(
                "Workflow can not be found with this id : '%s'. Error : %s",
                workflow_id,
                exception,
            )
