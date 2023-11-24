"""Test suite for the Lex Persona Signature Backend delete_signing_procedure"""
from django.test import TestCase
from django.test.utils import override_settings

import responses

from joanie.signature import exceptions
from joanie.signature.backends import get_signature_backend


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
    """Test suite for Lex Persona Signature provider Backend delete_signing_procedure."""

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
