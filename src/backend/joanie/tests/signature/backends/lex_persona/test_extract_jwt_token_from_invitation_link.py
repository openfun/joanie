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
