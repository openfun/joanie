"""Test suite for the Lex Persona Signature Backend sign_specific_selection_of_references"""
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
class LexPersonaBackendSignSpecificSelectionOfReferencesTestCase(TestCase):
    """Test suite for Lex Persona Signature provider Backend
    sign_specific_selection_of_references."""

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
