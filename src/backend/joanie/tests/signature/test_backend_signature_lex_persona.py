"""Test suite for the Lex Persona Signature Backend with mocking responses"""
# pylint: disable=too-many-public-methods, too-many-lines, protected-access
import json
from datetime import timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone as django_timezone

import responses

from joanie.core import factories
from joanie.signature import exceptions
from joanie.signature.backends import get_signature_backend
from joanie.signature.backends.lex_persona import LexPersonaBackend


@override_settings(
    JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.lex_persona.LexPersonaBackend",
    JOANIE_SIGNATURE_LEXPERSONA_BASE_URL="https://lex_persona.test01.com",
    JOANIE_SIGNATURE_LEXPERSONA_CONSENT_PAGE_ID="cop_id_fake",
    JOANIE_SIGNATURE_LEXPERSONA_SESSION_USER_ID="usr_id_fake",
    JOANIE_SIGNATURE_LEXPERSONA_PROFILE_ID="sip_profile_id_fake",
    JOANIE_SIGNATURE_LEXPERSONA_TOKEN="token_id_fake",
    JOANIE_SIGNATURE_VALIDITY_PERIOD=60 * 60 * 24 * 15,
    JOANIE_SIGNATURE_TIMEOUT=3,
)
class LexPersonaBackendTestCase(TestCase):
    """Test suite for Lex Persona Signature provider Backend."""

    @responses.activate
    def test_backend_lex_persona_create_workflow(self):
        """
        When creating a signature procedure with the signature provider, it should return
        the workflow's reference 'id' of the submission.
        """
        api_url = "https://lex_persona.test01.com/api/users/usr_id_fake/workflows"
        expected_response_data = {
            "created": 1696238245608,
            "currentRecipientEmails": [],
            "currentRecipientUsers": [],
            "description": "Contract Definition",
            "email": "johndoe@example.fr",
            "firstName": "John",
            "groupId": "grp_id_fake",
            "id": "wfl_id_fake",
            "lastName": "Doe",
            "logs": [],
            "name": "Contract Definition",
            "notifiedEvents": [
                "recipientRefused",
                "recipientFinished",
                "workflowStopped",
                "workflowFinished",
            ],
            "progress": 0,
            "steps": [
                {
                    "allowComments": True,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": True,
                    "id": "stp_J5gCgaRRY4NHtbGs474WjMkA",
                    "invitePeriod": None,
                    "isFinished": False,
                    "isStarted": False,
                    "logs": [],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "consentPageId": "cop_id_fake",
                            "country": "FR",
                            "email": "johnnydoe@example.fr",
                            "firstName": "Johnny",
                            "lastName": "Doe",
                            "preferredLocale": "fr",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": 86400000,
                }
            ],
            "tenantId": "ten_id_fake",
            "updated": 1696238245608,
            "userId": "usr_id_fake",
            "viewAuthorizedGroups": ["grp_id_fake"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "stopped",
        }
        backend = get_signature_backend()

        responses.add(
            responses.POST,
            api_url,
            status=200,
            json=expected_response_data,
        )
        reference = backend._create_workflow(
            title="Contract Definition",
            recipient_data={
                "email": "johnnydoe@example.fr",
                "firstName": "Johnny",
                "lastName": "Doe",
                "preferredLocale": "fr",
            },
        )

        self.assertEqual(expected_response_data["id"], reference)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertIsNotNone(responses.calls[0].request.body)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")

    @responses.activate
    def test_backend_lex_persona_create_workflow_failed(self):
        """
        If some required values in the payload are missing when creating the signature procedure,
        it will raise the exception Create Workflow Signature Failed.
        """
        api_url = "https://lex_persona.test01.com/api/users/usr_id_fake/workflows"
        backend = get_signature_backend()

        responses.add(
            responses.POST,
            api_url,
            status=400,
            json={
                "status": 400,
                "error": "Bad Request",
                "message": "A recipient in the request is missing identity information.",
                "requestId": "8cecebbd-235860",
                "code": "RecipientInfoMissing",
                "logId": "log_8vxLbfT6i8TtEZ2mu8wN9z3p",
            },
        )
        with self.assertRaises(exceptions.CreateSignatureProcedureFailed) as context:
            backend._create_workflow(title="Test Name Workflow", recipient_data={})

        self.assertEqual(
            str(context.exception),
            "Cannot create a signature procedure.",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")

    @responses.activate
    def test_backend_lex_persona_upload_file_to_workflow(self):
        """
        When uploading the file to an existing signature procedure, it should return the hash of
        the file when it suceeds.
        """
        workflow_id = "wfl_id_fake"
        api_url = (
            f"https://lex_persona.test01.com/api/workflows/{workflow_id}"
            "/parts?createDocuments=true&ignoreAttachments=false"
            "&signatureProfileId=sip_profile_id_fake&unzip=false&pdf2pdfa=auto"
        )
        expected_response_data = {
            "documents": [
                {
                    "created": 1696238255558,
                    "groupId": "grp_id_fake",
                    "id": "doc_id_fake",
                    "parts": [
                        {
                            "contentType": "application/pdf",
                            "filename": "contract_definition.pdf",
                            "hash": "wpTD3tstfdt9XfuFK+sv4/y6fv3lx3hwZ2gjQ2DBrxs=",
                            "size": 123616,
                        }
                    ],
                    "signatureProfileId": "sip_profile_id_fake",
                    "tenantId": "ten_id_fake",
                    "updated": 1696238255558,
                    "userId": "usr_id_fake",
                    "viewAuthorizedGroups": ["grp_id_fake"],
                    "viewAuthorizedUsers": [],
                    "workflowId": "wfl_id_fake",
                    "workflowName": "Heavy Duty Wool Watch",
                }
            ],
            "ignoredAttachments": 0,
            "parts": [
                {
                    "contentType": "application/pdf",
                    "filename": "contract_definition.pdf",
                    "hash": "wpTD3tstfdt9XfuFK+sv4/y6fv3lx3hwZ2gjQ2DBrxs=",
                    "size": 123616,
                }
            ],
        }
        file_bytes = b"Some fake content"
        backend = get_signature_backend()

        responses.add(responses.POST, api_url, status=200, json=expected_response_data)
        file_hash = backend._upload_file_to_workflow(file_bytes, workflow_id)

        self.assertEqual(file_hash, expected_response_data["parts"][0].get("hash"))
        self.assertEqual(
            expected_response_data.get("documents")[0].get("workflowId"),
            workflow_id,
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertIsNotNone(responses.calls[0].request.body)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")

    @responses.activate
    def test_backend_lex_persona_upload_file_failed(self):
        """
        When uploading a file to the signature procedure fails, it should raise the exception
        Upload Document Failed.
        """
        api_url = (
            "https://lex_persona.test01.com/api/workflows/wfl_id_fake"
            "/parts?createDocuments=true&ignoreAttachments=false"
            "&signatureProfileId=sip_profile_id_fake&unzip=false&pdf2pdfa=auto"
        )
        backend = get_signature_backend()

        responses.add(
            responses.POST,
            api_url,
            status=403,
            json={
                "status": 403,
                "error": "Forbidden",
                "message": "The specified signature profile is not allowed for this document.",
                "requestId": "b609eeba-546171",
                "code": "SignatureProfileNotAllowed",
                "logId": "log_GLDiyBejx5foCZ9VgLYSkkX6",
            },
        )
        with self.assertRaises(exceptions.UploadFileFailed) as context:
            backend._upload_file_to_workflow(b"not_a_file", "wfl_id_fake")

        self.assertEqual(
            str(context.exception),
            "Cannot upload the file to the signature provider with the signature reference.",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")

    @responses.activate
    def test_backend_lex_persona_start_workflowstatus(self):
        """
        When updating an existing signature procedure to start, it should change its
        'workflowStatus' to 'started'.
        """
        reference_id = "wfl_id_fake"
        api_url = f"https://lex_persona.test01.com/api/workflows/{reference_id}"
        expected_response_data = {
            "created": 1696238245608,
            "currentRecipientEmails": [],
            "currentRecipientUsers": [],
            "description": "1 rue de l'exemple, 75000 Paris",
            "email": "johndoe@example.fr",
            "firstName": "John",
            "groupId": "grp_id_fake",
            "id": "wfl_id_fake",
            "lastName": "Doe",
            "logs": [],
            "name": "Heavy Duty Wool Watch",
            "notifiedEvents": [
                "recipientRefused",
                "recipientFinished",
                "workflowStopped",
                "workflowFinished",
            ],
            "progress": 0,
            "steps": [
                {
                    "allowComments": True,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": True,
                    "id": "stp_J5gCgaRRY4NHtbGs474WjMkA",
                    "invitePeriod": None,
                    "isFinished": False,
                    "isStarted": False,
                    "logs": [],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "consentPageId": "cop_id_fake",
                            "country": "FR",
                            "email": "johnnydoe@example.fr",
                            "firstName": "Johnny",
                            "lastName": "Doe",
                            "preferredLocale": "fr",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": 86400000,
                }
            ],
            "tenantId": "ten_id_fake",
            "updated": 1696238262735,
            "userId": "usr_id_fake",
            "viewAuthorizedGroups": ["grp_id_fake"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "started",
        }
        backend = get_signature_backend()

        responses.add(responses.PATCH, api_url, status=200, json=expected_response_data)
        backend._start_procedure(reference_id)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.body, b'{"workflowStatus": "started"}'
        )
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "PATCH")

    @responses.activate
    def test_backend_lex_persona_start_workflow_failed(self):
        """
        When starting a signature procedure that does not exist, it should
        raise the exception Start Signature Procedure Failed.
        """
        api_url = (
            "https://lex_persona.test01.com/api/workflows/wfl_id_fake_does_not_exist"
        )
        backend = get_signature_backend()

        responses.add(
            responses.PATCH, api_url, json={"workflowStatus": "started"}, status=400
        )
        with self.assertRaises(exceptions.StartSignatureProcedureFailed) as context:
            backend._start_procedure(reference_id="wfl_id_fake_does_not_exist")

        self.assertEqual(
            str(context.exception),
            "Cannot start the signature procedure with signature reference",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "PATCH")

    @responses.activate
    def test_backend_lex_persona_sign_specific_selection_of_references(self):
        """
        When retrieving the invitation link to sign a specific selection of workflow
        that exist, it should return the 'consentPageUrl' to go sign the files.
        """
        api_url = "https://lex_persona.test01.com/api/requests/"
        expected_response_data = {
            "consentPageId": "cop_id_fake",
            "consentPageUrl": (
                "https://lex_persona.test01.com/?"
                "requestToken=eyJhbGciOiJIUzI1NiJ9#requestId=req_8KVKj7qNKNDgsN7Txx1sdvaT"
            ),
            "created": 1696238302063,
            "id": "req_id_fake",
            "steps": [
                {
                    "allowComments": True,
                    "stepId": "stp_id_fake",
                    "workflowId": "wfl_id_fake",
                }
            ],
            "tenantId": "ten_id_fake",
            "updated": 1696238302063,
        }
        backend = get_signature_backend()

        responses.add(
            responses.POST,
            api_url,
            json=expected_response_data,
            status=200,
        )

        result = backend._sign_specific_selection_of_references(
            reference_ids=["wfl_id_fake"], token_jwt="token_jwt_fake"
        )

        self.assertEqual(
            result.json().get("consentPageUrl"),
            expected_response_data["consentPageUrl"],
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            responses.calls[0].request.body, b'{"workflows": ["wfl_id_fake"]}'
        )
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_jwt_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")

    @responses.activate
    def test_backend_lex_persona_sign_selection_of_workflow_failed(self):
        """
        When retrieving the invitation link to sign a specific selection of workflow
        that do not exist, it should raise the exception Invitation Signature Failed.
        """
        api_url = "https://lex_persona.test01.com/api/requests/"
        backend = get_signature_backend()

        responses.add(
            responses.POST,
            api_url,
            status=404,
            json={
                "status": 404,
                "error": "Not Found",
                "message": "The specified workflow can not be found.",
                "requestId": "ff0b01d0-544232",
                "code": "WorkflowNotFound",
                "logId": "log_Hb9MzMUz83uo3ipD7ecuuZYp",
            },
        )
        with self.assertRaises(exceptions.InvitationSignatureFailed) as context:
            backend._sign_specific_selection_of_references(
                reference_ids=["wfl_id_fake_not_exist"], token_jwt="token_jwt_fake"
            )

        self.assertEqual(
            str(context.exception),
            "Cannot get invitation link to sign the file from the signature provider.",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_jwt_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")

    @responses.activate
    def test_backend_lex_persona_create_invitation_link_to_sign(self):
        """
        When retrieving an invitation link to sign the file, it should return the 'inviteUrl'
        to sign the file.
        """
        api_url = "https://lex_persona.test01.com/api/workflows/wfl_id_fake/invite"
        expected_response_data = {
            "inviteUrl": "https://lex_persona.test01.com/invite?token=eyJhbGciOiJIUzI1NiJ9"
        }
        backend = get_signature_backend()

        responses.add(
            responses.POST,
            api_url,
            json=expected_response_data,
            status=200,
        )
        result = backend._create_invitation_link_to_sign(
            recipient_email="johnnydo@example.fr", reference_id="wfl_id_fake"
        )

        self.assertEqual(result.json(), expected_response_data)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            responses.calls[0].request.body,
            b'{"recipientEmail": "johnnydo@example.fr"}',
        )
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")

    @responses.activate
    def test_backend_lex_persona_create_invitation_link_to_sign_failed(self):
        """
        When retrieving the invitation link fails, it should raise the exception Invitation
        Signature Failed because the signature procedure has not started yet.
        """
        api_url = "https://lex_persona.test01.com/api/workflows/wfl_id_fake/invite"
        backend = get_signature_backend()

        responses.add(
            responses.POST,
            api_url,
            status=403,
            json={
                "status": 403,
                "error": "Forbidden",
                "message": "The status of the workflow does not allow this operation.",
                "requestId": "f1ae1413-540524",
                "code": "InvalidWorkflowStatus",
                "logId": "log_NCBijyAjxKAKdPTyW1VrEGbE",
            },
        )
        with self.assertRaises(exceptions.InvitationSignatureFailed) as context:
            backend._create_invitation_link_to_sign(
                recipient_email="johnnydo@example.fr", reference_id="wfl_id_fake"
            )

        self.assertEqual(
            str(context.exception),
            "johnnydo@example.fr has no documents registered to sign at the moment.",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")
        responses.reset()

    @responses.activate
    def test_backend_lex_persona_delete_signing_procedure(self):
        """
        When deleting a signature procedure with its signature backend reference that exists,
        it should change the 'workflowStatus' to 'stopped'.
        """
        api_url = "https://lex_persona.test01.com/api/workflows/wfl_id_fake"
        expected_response_data = {
            "created": 1696238245608,
            "currentRecipientEmails": [],
            "currentRecipientUsers": [],
            "description": "1 rue de l'exemple, 75000 Paris",
            "email": "johndoe@example.fr",
            "firstName": "John",
            "groupId": "grp_id_fake",
            "id": "wfl_id_fake",
            "lastName": "Doe",
            "logs": [],
            "name": "Heavy Duty Wool Watch",
            "notifiedEvents": [
                "recipientRefused",
                "recipientFinished",
                "workflowStopped",
                "workflowFinished",
            ],
            "progress": 0,
            "steps": [
                {
                    "allowComments": True,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": True,
                    "id": "stp_J5gCgaRRY4NHtbGs474WjMkA",
                    "invitePeriod": None,
                    "isFinished": False,
                    "isStarted": False,
                    "logs": [],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "consentPageId": "cop_id_fake",
                            "country": "FR",
                            "email": "johnnydoe@example.fr",
                            "firstName": "Johnny",
                            "lastName": "Doe",
                            "preferredLocale": "fr",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": 86400000,
                }
            ],
            "tenantId": "ten_id_fake",
            "updated": 1696238262735,
            "userId": "usr_id_fake",
            "viewAuthorizedGroups": ["grp_id_fake"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "stopped",
        }
        backend = get_signature_backend()

        responses.add(
            responses.DELETE,
            api_url,
            json=expected_response_data,
            status=200,
        )
        result = backend.delete_signing_procedure(reference_id="wfl_id_fake")

        self.assertEqual(result, expected_response_data)

        self.assertEqual(result["workflowStatus"], "stopped")
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "DELETE")

    @responses.activate
    def test_backend_lex_persona_delete_signing_procedure_failed(self):
        """
        When deleting a signature procedure with a reference that does not exist or that is
        finished, it should raise Delete Workflow Signature Failed.
        """
        api_url = "https://lex_persona.test01.com/api/workflows/wfl_id_fake"
        backend = get_signature_backend()

        responses.add(
            responses.DELETE,
            api_url,
            status=404,
            json={
                "status": 404,
                "error": "Not Found",
                "message": "The specified workflow can not be found.",
                "requestId": "d44f8bf6-1244051",
                "code": "WorkflowNotFound",
                "logId": "log_F9bcd1sayk7aMWLYSK4QxEVt",
            },
        )
        with self.assertRaises(exceptions.DeleteSignatureProcedureFailed) as context:
            backend.delete_signing_procedure(reference_id="wfl_id_fake")

        self.assertEqual(
            str(context.exception),
            "Unable to delete the signature procedure the reference does not exist wfl_id_fake",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "DELETE")

    @responses.activate
    def test_backend_lex_persona_verify_webhook_event_returns_true(self):
        """
        When verifying the incoming webhook event that exist at the signature provider,
        it should return True.
        """
        api_url = "https://lex_persona.test01.com/api/webhookEvents/wbe_id_fake"
        expected_response_data = {
            "created": 1695518537020,
            "eventType": "workflowFinished",
            "id": "wbe_id_fake",
            "tenantId": "ten_id_fake",
            "updated": 1695518570617,
            "userId": "usr_id_fake",
            "webhookId": "wbh_id_fake",
            "workflowId": "wfl_id_fake",
        }
        backend = get_signature_backend()

        responses.add(responses.GET, api_url, json=expected_response_data, status=200)
        result = backend._verify_webhook_event(webhook_event_id="wbe_id_fake")

        self.assertEqual(result, expected_response_data)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "GET")

    @responses.activate
    def test_backend_lex_persona_verify_webhook_event_returns_false(self):
        """
        When verifying the incoming webhook event that does not exist at the signature provider,
        it should return False.
        """
        api_url = "https://lex_persona.test01.com/api/webhookEvents/wbe_id_fake_does_not_exist"
        expected_response_data = {
            "status": 404,
            "error": "Not Found",
            "message": "The specified webhook event can not be found.",
            "requestId": "379a3980-481772",
            "code": "WebhookEventNotFound",
        }
        backend = get_signature_backend()

        responses.add(responses.GET, api_url, json=expected_response_data, status=400)
        with self.assertRaises(ValidationError) as context:
            backend._verify_webhook_event(webhook_event_id="wbe_id_fake_does_not_exist")

        self.assertEqual(
            str(context.exception),
            "['Unable to verify the webhook event with the signature provider.']",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "GET")

    @responses.activate
    def test_backend_lex_persona_get_jwt_token_from_invitation_link(self):
        """
        When retrieving the JWT token from the invitation link, it should return the expected value
        in order to use it for the '_sign_specific_selection_of_references' method.
        """
        api_url = "https://lex_persona.test01.com/api/workflows/wfl_id_fake/invite"
        recipient_email = "johnnydo@example.com"
        expected_response_data = {
            "inviteUrl": "https://example.com/invite?token=fake_sample_token"
        }
        backend = get_signature_backend()

        responses.add(responses.POST, api_url, json=expected_response_data)
        token = backend._get_jwt_token_from_invitation_link(
            recipient_email=recipient_email, reference_id="wfl_id_fake"
        )

        self.assertEqual(token, "fake_sample_token")
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )

    @responses.activate
    def test_backend_lex_persona_get_jwt_token_fails_because_get_invitation_link_fails(
        self,
    ):
        """
        When retrieving the JWT token from the invitation link of a signature procedure
        reference that does not exist or/and the recipient email has no file signed,
        it should raise Invitation Signature Failed.
        """
        api_url = "https://lex_persona.test01.com/api/workflows/wfl_id_fake/invite"
        backend = get_signature_backend()

        responses.add(
            responses.POST,
            api_url,
            json={"error": "Failed to create invitation link"},
            status=400,
        )
        with self.assertRaises(exceptions.InvitationSignatureFailed) as context:
            backend._get_jwt_token_from_invitation_link(
                recipient_email="johnnydo@example.fr", reference_id="wfl_id_fake"
            )

        self.assertEqual(
            str(context.exception),
            "johnnydo@example.fr has no documents registered to sign at the moment.",
        )

    def test_backend_lex_persona_extract_jwt_token(self):
        """
        When extracting the token from the invitation link, it should return the JWT token's
        value as a string.
        """
        invitation_url = "https://example.com/invite?token=fake_sample_jwt_token_found"
        backend = get_signature_backend()

        extracted_token = backend._extract_jwt_token_from_invitation_link(
            invitation_url
        )

        self.assertEqual(extracted_token, "fake_sample_jwt_token_found")

    def test_backend_lex_persona_extract_jwt_token_missing_token_in_invite_url(self):
        """
        When there is no token to extract from the invitation URL, it should raise the exception
        ValueError
        """
        invitation_url = "https://example.com/invite"
        backend = get_signature_backend()

        with self.assertRaises(ValueError) as context:
            backend._extract_jwt_token_from_invitation_link(invitation_url)

        self.assertEqual(
            str(context.exception),
            "Cannot extract JWT Token from the invite url of the signature provider",
        )

    @mock.patch.object(LexPersonaBackend, "_verify_webhook_event")
    def test_backend_lex_persona_handle_notification_workflowstarted_unsupported_event_type(
        self, mock_verify_webhook_event
    ):
        """
        When an incoming webhook event type is 'workflowStarted', and the event is verified,
        it should raise the exception Handle Notification Failed because we don't track this
        specific event type.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowStarted",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        mock_verify_webhook_event.return_value = {
            "id": "wbe_id_fake",
            "tenantId": "ten_id_fake",
            "userId": "usr_id_fake",
            "webhookId": "wbh_id_fake",
            "workflowId": "wfl_id_fake",
            "stepId": "stp_id_fake",
            "eventType": "workflowStarted",
            "created": 1693404075146,
            "updated": 1693404075146,
        }
        backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "['The notification workflowStarted is not supported.']",
        )

    @mock.patch.object(LexPersonaBackend, "_verify_webhook_event")
    def test_backend_lex_persona_handle_notification_workflowstopped_unsupported_event_type(
        self, mock_verify_webhook_event
    ):
        """
        When an incoming webhook event type is 'workflowStopped', and the event is verified,
        it should raise an exception because we don't track this specific event type.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowStopped",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        mock_verify_webhook_event.return_value = {
            "id": "wbe_id_fake",
            "tenantId": "ten_id_fake",
            "userId": "usr_id_fake",
            "webhookId": "wbh_id_fake",
            "workflowId": "wfl_id_fake",
            "stepId": "stp_id_fake",
            "eventType": "workflowStopped",
            "created": 1693404075146,
            "updated": 1693404075146,
        }
        backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "['The notification workflowStopped is not supported.']",
        )

    def test_backend_lex_persona_handle_notification_incoming_request_body_is_an_empty_dictionary(
        self,
    ):
        """
        When an incoming webhook event is an empty dictionary, it should raise Retrieve Key Failed
        because the request body is missing the key 'id' we want to retrieve.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": b"{}",
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        backend = get_signature_backend()

        with self.assertRaises(KeyError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "'Missing the key id to retrieve from the webhook event data'",
        )

    def test_backend_lex_persona_handle_notification_body_is_missing_id_key(self):
        """
        When an incoming webhook event is missing the 'id' key, it should raise
        the exception KeyError because we can't verify the webhook event reference.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowFinished",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        backend = get_signature_backend()

        with self.assertRaises(KeyError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "'Missing the key id to retrieve from the webhook event data'",
        )

    def test_backend_lex_persona_handle_notification_with_malformed_json_body(self):
        """
        When an incoming webhook event has a malformed JSON body, it should raise the exception
        ValidationError.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": "malformed JSON body",
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception), "['The JSON body of the request is malformed']"
        )

    @mock.patch.object(LexPersonaBackend, "_verify_webhook_event")
    def test_backend_lex_persona_handle_notification_verify_webhook_event_failed_to_verify(
        self, mock_verify_webhook_event
    ):
        """
        When an incoming event type is 'workflowFinished', but we can't verify that webhook event
        authenticity and integrity, it should raise ValidationError.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowFinished",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        mock_verify_webhook_event.side_effect = ValidationError(
            "['Unable to verify the webhook event with the signature provider.']"
        )
        backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "['Unable to verify the webhook event with the signature provider.']",
        )

    @mock.patch.object(LexPersonaBackend, "_verify_webhook_event")
    def test_backend_lex_persona_handle_notification_workflow_finished_event(
        self, mock_verify_webhook_event
    ):
        """
        When an incoming event type is 'workflowFinished', and the event has been verified,
        then the contract which has the signature backend reference should get updated
        with a new 'signed_on' date and update the value of 'submitted_for_signature_on' to None.
        """
        user = factories.UserFactory(email="johnnydo@example.fr")
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_id_fake",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now(),
        )
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowFinished",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        mock_verify_webhook_event.return_value = {
            "id": "wbe_id_fake",
            "tenantId": "ten_id_fake",
            "userId": "usr_id_fake",
            "webhookId": "wbh_id_fake",
            "workflowId": "wfl_id_fake",
            "stepId": "stp_id_fake",
            "eventType": "workflowFinished",
            "created": 1693404075146,
            "updated": 1693404075146,
        }
        backend = get_signature_backend()

        backend.handle_notification(request)

        contract.refresh_from_db()
        self.assertIsNotNone(contract.signed_on)
        self.assertIsNone(contract.submitted_for_signature_on)

    @override_settings(
        JOANIE_SIGNATURE_VALIDITY_PERIOD=60 * 60 * 24 * 15,
    )
    @mock.patch.object(LexPersonaBackend, "_verify_webhook_event")
    def test_backend_lex_persona_handle_notification_workflow_finished_event_but_signature_expired(
        self, mock_verify_webhook_event
    ):
        """
        When an incoming event type is 'workflowFinished' and the 'id' has been verified at the
        signature provider, but the expiration date to sign has passed, then we should raise an
        error. The file is eligible for a signature for a period of 15 days.
        """
        user = factories.UserFactory(email="johnnydo@example.fr")
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_id_fake",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now() - timedelta(days=16),
        )
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowFinished",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        mock_verify_webhook_event.return_value = {
            "id": "wbe_id_fake",
            "tenantId": "ten_id_fake",
            "userId": "usr_id_fake",
            "webhookId": "wbh_id_fake",
            "workflowId": "wfl_id_fake",
            "stepId": "stp_id_fake",
            "eventType": "workflowFinished",
            "created": 1693404075146,
            "updated": 1693404075146,
        }
        backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "['The contract validity date of expiration has passed.']",
        )
        self.assertIsNotNone(contract.submitted_for_signature_on)
        self.assertIsNone(contract.signed_on)

    @mock.patch.object(LexPersonaBackend, "_verify_webhook_event")
    def test_backend_lex_persona_handle_notification_recipient_refused_should_reset_contract(
        self, mock_verify_webhook_event
    ):
        """
        When an incoming event type is 'recipientRefused', and the event has been verified,
        then the contract which has the signature backend reference should be reset on the
        fields : 'context', 'submitted_for_signature_on' 'signature_backend_reference' and
        'definition_checksum' to None.
        """
        user = factories.UserFactory(email="johnnydo@example.fr")
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_id_fake",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now(),
        )
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "recipientRefused",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        mock_verify_webhook_event.return_value = {
            "id": "wbe_id_fake",
            "tenantId": "ten_id_fake",
            "userId": "usr_id_fake",
            "webhookId": "wbh_id_fake",
            "workflowId": "wfl_id_fake",
            "stepId": "stp_id_fake",
            "eventType": "recipientRefused",
            "created": 1693404075146,
            "updated": 1693404075146,
        }
        backend = get_signature_backend()

        backend.handle_notification(request)

        contract.refresh_from_db()
        self.assertIsNone(contract.signed_on)
        self.assertIsNone(contract.context)
        self.assertIsNone(contract.submitted_for_signature_on)
        self.assertIsNone(contract.signature_backend_reference)
        self.assertIsNone(contract.definition_checksum)

    def test_backend_lex_persona_prepare_recipient_information_of_the_signer(self):
        """
        When we prepare the payload to create a signature procedure, it should
        return a list with a dictionnary of the owner's information.
        """
        user = factories.UserFactory(email="johnnydo@example.fr")
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(owner=user)
        country = order.owner.addresses.filter(is_main=True).first().country.code
        backend = get_signature_backend()
        expected_prepared_recipient_data = [
            {
                "email": order.owner.email,
                "firstName": order.owner.first_name,
                "lastName": ".",
                "country": country.upper(),
                "preferred_locale": order.owner.language.lower(),
                "consentPageId": "cop_id_fake",
            }
        ]

        recipient_data = backend._prepare_recipient_information_of_the_signer(order)

        self.assertEqual(recipient_data, expected_prepared_recipient_data)
