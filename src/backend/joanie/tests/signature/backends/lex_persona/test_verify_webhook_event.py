"""Test suite for the Lex Persona Signature Backend verify_webhook_event"""
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings

import responses

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
class LexPersonaBackendVerifyWebhookEventTestCase(TestCase):
    """Test suite for Lex Persona Signature provider Backend verify_webhook_event."""

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
            "['Lex Persona: Unable to verify the webhook event with the signature provider.']",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "GET")
