"""Test suite for the Lex Persona Signature Backend create_invitation_link_to_sign"""
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
class LexPersonaBackendCreateInvitationLinkToSignTestCase(TestCase):
    """Test suite for Lex Persona Signature provider Backend create_invitation_link_to_sign."""

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
