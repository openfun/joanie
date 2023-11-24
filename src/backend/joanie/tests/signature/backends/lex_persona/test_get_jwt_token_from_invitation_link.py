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
