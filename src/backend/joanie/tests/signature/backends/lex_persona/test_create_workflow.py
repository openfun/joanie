"""Test suite for the Lex Persona Signature Backend create_workflow"""
from django.test import TestCase
from django.test.utils import override_settings

import responses

from joanie.signature import exceptions
from joanie.signature.backends import get_signature_backend

# pylint: disable=protected-access


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
class LexPersonaBackendCreateWorkflowTestCase(TestCase):
    """Test suite for Lex Persona Signature provider Backend create_workflow."""

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
            "Lex Persona: Cannot create a signature procedure.",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")
