"""Test suite of the DummySignatureBackend"""
from django.core.cache import cache

from joanie.signature.backends.base import BaseSignatureBackend
from joanie.signature.backends.dummy import DummySignatureBackend

from .base_signature import BaseSignatureTestCase


# pylint: disable=protected-access
# pylint: disable=too-many-public-methods
class DummySignatureBackendTestCase(BaseSignatureTestCase):
    """Test case for the Dummy Signature Backend."""

    def setUp(self):
        """Clears the cache before each test"""
        cache.clear()

    def test_signature_backend_dummy_name(self):
        """Dummy backend instance name is dummy and required recipient is 1."""
        backend = DummySignatureBackend()
        self.assertEqual(backend.name, "dummy")
        self.assertIsInstance(backend, BaseSignatureBackend)
        self.assertEqual(backend.required_recipients, 1)

    def test_signature_backend_dummy_upload_file_cache_checkup_data(self):
        """Dummy backend instance upload a file."""
        backend = DummySignatureBackend()
        response = backend.upload_file()
        workflow_item = response["items"][0]
        expected_recipients = {
            "student_do@example.fr": False,
        }
        self.assertEqual(workflow_item["recipients"], expected_recipients)
        self.assertEqual(workflow_item["provider"], "dummy")
        self.assertEqual(workflow_item["requiredRecipients"], 1)
        self.assertEqual(workflow_item["parts"], "template.pdf")
        self.assertEqual(workflow_item["workflowStatus"], "started")

    def test_signature_backend_dummy_create_invitation_link_with_invalid_email(self):
        """
        Dummy backend instance tries to create invitation link with
        an unregistered email for the signature procedure. It shall raise a ValueError.
        """
        backend = DummySignatureBackend()
        create_response = backend.upload_file()
        kwargs = {"workflow_id": create_response["items"][0]["id"]}
        with self.assertRaises(ValueError) as context:
            backend.create_invitation_link(
                recipient_email="johndoe@example.fr", **kwargs
            )
        self.assertEqual(
            str(context.exception),
            "Your recipient email johndoe@example.fr is not correct, try again",
        )

        with self.assertRaises(ValueError) as context:
            backend.create_invitation_link(
                recipient_email="johndoeteacher@example.fr", **kwargs
            )
        self.assertEqual(
            str(context.exception),
            "Your recipient email johndoeteacher@example.fr is not correct, try again",
        )

    def test_signature_backend_dummy_create_invitation_link_valid_email_student(self):
        """
        Dummy backend instance create invitation link with a registered email
        of a student for the signature procedure. We should find with the webhook
        mechanism the events in cache.
        """
        backend = DummySignatureBackend()
        create_response = backend.upload_file()
        kwargs = {"workflow_id": create_response["items"][0]["id"]}
        invite_url_student = backend.create_invitation_link(
            recipient_email="student_do@example.fr", **kwargs
        )
        expected_recipients = {
            "student_do@example.fr": True,
        }

        workflow_data = backend._get_cache_data()
        workflow_item = workflow_data["items"][0]
        self.assertEqual(backend.required_recipients, 1)
        self.assertEqual(workflow_item["recipients"], expected_recipients)
        expected_substring = "https://dummysignaturebackend.fr/invite?"
        self.assertIn(expected_substring, invite_url_student["inviteUrl"])
        self.assertEqual(workflow_item["workflowStatus"], "finished")

        self.assertEqual(len(workflow_item["webhook_events_id"]), 1)
        self.assertEqual(
            workflow_item["webhook_events_detail"][0]["eventType"],
            "workflowFinished",
        )
        self._check_signature_completed_email_sent(
            "student_do@example.fr",
            workflow_item["id"],
        )

    def test_signature_backend_dummy_handle_notification_recipient_refused(self):
        """
        Dummy backend instance to mock incoming POST request
        for the webhook mecanism when recipient has refused the invitation link.
        """
        backend = DummySignatureBackend()
        create_response = backend.upload_file()
        kwargs = {"workflow_id": create_response["items"][0]["id"]}

        backend.create_invitation_link(
            recipient_email="student_do@example.fr", **kwargs
        )
        updated_info = backend._get_cache_data()
        workflow_item = updated_info["items"][0]
        latest_event = workflow_item["webhook_events_id"][0]
        request_body = {
            "eventType": "recipientRefused",
            "id": latest_event,
            "workflowId": workflow_item["id"],
        }
        result = backend.handle_notification(request=request_body)
        self.assertEqual(result, "Document Signature has been aborted")

    def test_signature_backend_dummy_handle_notification_workflow_finished(self):
        """
        Dummy backend instance to mock incoming POST request
        for the webhook mecanism when workflow is finished.
        """
        backend = DummySignatureBackend()
        create_response = backend.upload_file()
        kwargs = {"workflow_id": create_response["items"][0]["id"]}

        backend.create_invitation_link(
            recipient_email="student_do@example.fr", **kwargs
        )

        updated_info = backend._get_cache_data()
        workflow_item = updated_info["items"][0]

        latest_event = workflow_item["webhook_events_id"][0]
        request_body = {
            "eventType": "workflowFinished",
            "id": latest_event,
            "workflowId": workflow_item["id"],
        }
        result = backend.handle_notification(request=request_body)
        self.assertEqual(result, "All parties have signed the document")

    def test_signature_backend_dummy_handle_notification_unauthorized_event(self):
        """
        Dummy backend instance to mock incoming POST request
        for the webhook mecanism when unauthorized event occur.
        """
        backend = DummySignatureBackend()
        create_response = backend.upload_file()
        kwargs = {"workflow_id": create_response["items"][0]["id"]}

        backend.create_invitation_link(
            recipient_email="student_do@example.fr", **kwargs
        )

        updated_info = backend._get_cache_data()
        workflow_item = updated_info["items"][0]

        latest_event = workflow_item["webhook_events_id"][0]
        request_body = {
            "eventType": "randomEvent",
            "id": latest_event,
            "workflowId": workflow_item["id"],
        }
        result = backend.handle_notification(request=request_body)
        self.assertEqual(result, "Failed, this event can not be verified")

    def test_signature_backend_dummy_get_document_onetime_url(self):
        """
        Dummy backend instance when a recipient email decides to download
        the document once all the required recipient have signed.

        If not all required recipients have signed, then the download
        is not available.
        """
        backend = DummySignatureBackend()
        create_response = backend.upload_file()
        workflow_id = create_response["items"][0]["id"]
        kwargs = {"workflow_id": workflow_id}

        result = backend.get_document_onetime_url(workflow_id)
        expected_result = (
            f"'{workflow_id}' is not yet finished, its current status is : 'started'"
        )
        self.assertIn(expected_result, result)

        backend.create_invitation_link(
            recipient_email="student_do@example.fr", **kwargs
        )
        workflow_data = backend._get_cache_data()
        workflow_item = workflow_data["items"][0]
        expected_recipients = {
            "student_do@example.fr": True,
        }
        self.assertEqual(workflow_item["recipients"], expected_recipients)
        status = workflow_item["workflowStatus"]
        workflow_id = workflow_item["id"]
        self.assertEqual(status, "finished")
        download_url = backend.get_document_onetime_url(workflow_id)
        expected_substring = "https://dummysignaturebackend.fr/download?url="
        self.assertIn(expected_substring, download_url["downloadUrl"])

    def test_signature_backend_dummy_get_signature_invitation_link(self):
        """
        Dummy backend instance to sign a selection of documents
        from their workflow id and the recipient email that is behind
        the action.

        Once all required recipients have signed, the webhook event
        detail should mention that the 'eventType' is 'workflowFinished'.
        """
        backend = DummySignatureBackend()
        backend.upload_file()
        workflow_data = backend._add_a_workflow_to_items()

        first_workflow_id = workflow_data["items"][0]["id"]
        second_workflow_id = workflow_data["items"][1]["id"]

        response = backend.get_signature_invitation_link(
            "student_do@example.fr",
            workflow_ids=[first_workflow_id, second_workflow_id],
        )
        expected_substring = "https://dummysignaturebackend.fr/?requestToken="
        self.assertIn(expected_substring, response["inviteUrlSelection"])

        cache_data = backend._get_cache_data()
        self.assertEqual(1, len(cache_data["items"][0]["webhook_events_detail"]))
        self.assertEqual(
            True, cache_data["items"][0]["recipients"]["student_do@example.fr"]
        )
        self.assertEqual(
            "workflowFinished",
            cache_data["items"][0]["webhook_events_detail"][0]["eventType"],
        )

    def test_signature_backend_dummy_add_workflow_to_items_in_cache(self):
        """
        Dummy backend instance when adding a new workflow (a new document to sign).
        The new information should be added into cache.
        """
        backend = DummySignatureBackend()
        backend.upload_file()

        workflow_data = backend._add_a_workflow_to_items()
        workflow_first = workflow_data["items"][0]
        workflow_second = workflow_data["items"][1]

        expected_cache = {
            "items": [
                {
                    "contract_id": str(workflow_first["contract_id"]),
                    "id": str(workflow_first["id"]),
                    "recipients": {
                        "student_do@example.fr": False,
                    },
                    "workflowStatus": "started",
                    "parts": "template.pdf",
                    "provider": str(workflow_first["provider"]),
                    "requiredRecipients": workflow_first["requiredRecipients"],
                    "webhook_events_id": [],
                    "webhook_events_detail": [],
                },
                {
                    "contract_id": str(workflow_second["contract_id"]),
                    "id": str(workflow_second["id"]),
                    "recipients": {
                        "student_do@example.fr": False,
                    },
                    "workflowStatus": "started",
                    "parts": "template_2.pdf",
                    "provider": str(workflow_second["provider"]),
                    "requiredRecipients": workflow_second["requiredRecipients"],
                    "webhook_events_id": [],
                    "webhook_events_detail": [],
                },
            ],
        }
        self.assertEqual(workflow_data, expected_cache)

    def test_signature_backend_dummy_get_document_onetime_url_when_it_has_been_refused(
        self,
    ):
        """
        Dummy backend instance should not respond with a download link
        for the document when it has been refused earlier by
        one recipient.
        """
        backend = DummySignatureBackend()
        backend.upload_file()
        workflow_data = backend._add_a_workflow_to_items()

        first_workflow_id = workflow_data["items"][0]["id"]
        workflow_ids = [first_workflow_id]
        result = backend.refuse_signature(
            recipient_email="student_do@example.fr", workflow_ids=workflow_ids
        )
        expected = {"success": workflow_ids, "fail": []}
        self.assertEqual(result, expected)

        download_link = backend.get_document_onetime_url(workflow_id=first_workflow_id)
        expected_download_link = (
            f"'{first_workflow_id}' has been refused, its current status is : 'stopped'"
        )
        self.assertEqual(download_link, expected_download_link)

    def test_signature_backend_dummy_refusal_signature_with_incorrect_workflow_id(self):
        """
        Dummy backend instance fails with an incorrect workflow id.
        """
        backend = DummySignatureBackend()
        backend.upload_file()
        result = backend.refuse_signature(
            recipient_email="student_do@example.fr",
            workflow_ids=["wlf_dummy_id_wrong"],
        )
        expected_result = {"success": [], "fail": ["wlf_dummy_id_wrong"]}
        self.assertEqual(result, expected_result)

    def test_signature_backend_dummy_refusal_procedure(self):
        """
        Dummy backend instance when a recipient email decides to refuse
        the signature of a document.
        The 'workflowStatus' will be 'stopped'
        """
        backend = DummySignatureBackend()
        create_response = backend.upload_file()
        workflow_id = create_response["items"][0]["id"]
        kwargs = {"workflow_id": workflow_id}
        backend.create_invitation_link(
            recipient_email="student_do@example.fr", **kwargs
        )
        workflow_data = backend._get_cache_data()
        workflow_item = workflow_data["items"][0]
        expected_recipients = {
            "student_do@example.fr": True,
        }
        self.assertEqual(workflow_item["recipients"], expected_recipients)
        refusal_email_address = "student_do@example.fr"
        result = backend.refuse_signature(
            recipient_email=refusal_email_address, workflow_ids=[workflow_id]
        )
        self.assertEqual(
            result,
            {"success": [workflow_id], "fail": []},
        )

        updated_workflow_data = backend._get_cache_data()
        updated_workflow_item = updated_workflow_data["items"][0]
        self.assertEqual(updated_workflow_item["workflowStatus"], "stopped")

    def test_signature_backend_dummy_refusal_signature_on_second_item_only(self):
        """
        Dummy backend instance if the recipient email refuses to sign
        the second item. Once this action is done, it should
        update the second item in cache for the 'workflowStatus' from
        the value 'started' to 'stopped'.
        """
        backend = DummySignatureBackend()
        backend.upload_file()
        workflow_data = backend._add_a_workflow_to_items()
        second_workflow_id = workflow_data["items"][1]["id"]
        result = backend.refuse_signature(
            recipient_email="student_do@example.fr", workflow_ids=[second_workflow_id]
        )
        expected = {"success": [second_workflow_id], "fail": []}
        self.assertEqual(result, expected)

        updated_workflow_data = backend._get_cache_data()
        self.assertEqual(workflow_data["items"][1]["workflowStatus"], "started")
        self.assertEqual(updated_workflow_data["items"][1]["workflowStatus"], "stopped")
        self.assertEqual(
            updated_workflow_data["items"][1]["webhook_events_detail"][-1]["eventType"],
            "recipientRefused",
        )

    def test_signature_backend_dummy_send_post_webhook_handling_refusal_procedure(self):
        """
        Dummy backend instance to mock the webhook POST request
        for the webhook mechanism for the refusal of signing a document.
        """
        backend = DummySignatureBackend()
        create_response = backend.upload_file()
        workflow_id = create_response["items"][0]["id"]
        refusal_email_address = "student_do@example.fr"
        result = backend.refuse_signature(
            recipient_email=refusal_email_address, workflow_ids=[workflow_id]
        )
        expected_result = {"success": [workflow_id], "fail": []}
        self.assertEqual(result, expected_result)
        updated_workflow_data = backend._get_cache_data()
        updated_workflow_item = updated_workflow_data["items"][0]
        self.assertEqual(updated_workflow_item["workflowStatus"], "stopped")
        self.assertEqual(
            updated_workflow_item["webhook_events_detail"][0]["eventType"],
            "recipientRefused",
        )
        self.assertEqual(len(updated_workflow_item["webhook_events_id"]), 1)
