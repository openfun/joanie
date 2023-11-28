"""Test suite for the Lex Persona Signature Backend get_signature_invitation_link"""
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
class LexPersonaBackendGetSignatureInvitationLinkTestCase(TestCase):
    """Tests for Lex persona get_signature_invitation_link"""

    # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_lex_persona_get_signature_invitation_link_success(self):
        """
        When retrieving the invitation link to sign a specific selection of workflow
        that exist, it should return the 'consentPageUrl' to go sign the files.
        """

        responses.add(
            responses.POST,
            "https://lex_persona.test01.com/api/workflows/wfl_id_fake/invite",
            json={"inviteUrl": "https://example.com/invite?token=jwt_token"},
            status=200,
            match=[
                responses.matchers.header_matcher(
                    {
                        "Authorization": "Bearer token_id_fake",
                    },
                ),
                responses.matchers.json_params_matcher(
                    {"recipientEmail": "johnnydo@example.com"}
                ),
            ],
        )

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

        responses.add(
            responses.POST,
            "https://lex_persona.test01.com/api/requests/",
            json=expected_response_data,
            status=200,
            match=[
                responses.matchers.header_matcher(
                    {
                        "Authorization": "Bearer jwt_token",
                    },
                ),
                responses.matchers.json_params_matcher(
                    {
                        "workflows": ["wfl_id_fake"],
                    }
                ),
            ],
        )

        backend = get_signature_backend()
        result = backend.get_signature_invitation_link(
            recipient_email="johnnydo@example.com", reference_ids=["wfl_id_fake"]
        )

        self.assertEqual(
            result,
            expected_response_data["consentPageUrl"],
        )

    @responses.activate
    def test_backend_lex_persona_get_signature_invitation_link_get_jwt_token_fails(
        self
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
            backend.get_signature_invitation_link(
                recipient_email="johnnydo@example.fr", reference_ids=["wfl_id_fake"]
            )

        self.assertEqual(
            str(context.exception),
            "Lex Persona: johnnydo@example.fr has no documents registered to sign at the moment.",
        )

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
        # Managed invitation link
        responses.add(
            responses.POST,
            "https://lex_persona.test01.com/api/workflows/wfl_id_fake_not_exist/invite",
            json={"inviteUrl": "https://example.com/invite?token=jwt_token"},
            status=200,
        )

        with self.assertRaises(exceptions.InvitationSignatureFailed) as context:
            backend.get_signature_invitation_link(
                recipient_email="johnnydo@example.com",
                reference_ids=["wfl_id_fake_not_exist"],
            )

        self.assertEqual(
            str(context.exception),
            "Lex Persona: Cannot get invitation link to sign the file from the signature provider.",
        )
        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(responses.calls[1].request.url, api_url)
        self.assertEqual(
            responses.calls[1].request.headers["Authorization"], "Bearer jwt_token"
        )
        self.assertEqual(responses.calls[1].request.method, "POST")

    @responses.activate
    def test_signature_invitation_link_missing_token_in_invite_url(self):
        """
        When there is no token to extract from the invitation URL, it should raise the exception
        ValueError
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

        responses.add(
            responses.POST,
            api_url,
            json=expected_response_data,
            status=200,
        )

        # Managed invitation link
        responses.add(
            responses.POST,
            "https://lex_persona.test01.com/api/workflows/wfl_id_fake/invite",
            json={"inviteUrl": "https://example.com/invite"},
            status=200,
        )

        backend = get_signature_backend()
        with self.assertRaises(ValueError) as context:
            backend.get_signature_invitation_link(
                recipient_email="johnnydo@example.com", reference_ids=["wfl_id_fake"]
            )

        self.assertEqual(
            str(context.exception),
            "Cannot extract JWT Token from the invite url of the signature provider",
        )
