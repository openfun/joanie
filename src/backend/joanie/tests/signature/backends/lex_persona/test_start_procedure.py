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
