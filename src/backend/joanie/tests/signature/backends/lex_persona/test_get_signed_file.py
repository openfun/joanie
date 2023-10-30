"""Test suite for the Lex Persona Signature Backend get_signed_file"""
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings

import responses

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
class LexPersonaBackendGetSignedFileTestCase(TestCase):
    """Test for Lex Persona backend get_signed_file."""

    @responses.activate
    def test_backend_lex_persona_get_signed_file(self):
        """
        When we request to the signature provider that we want to retrieve a signed file
        through a specific signature backend reference, it should return the file if found
        as a PDF bytes.
        """
        reference_id = "wlf_dummy_id"
        url = f"https://lex_persona.test01.com/api/workflows/{reference_id}/downloadDocuments"
        pdf_content = b"Simulated PDF content in bytes from signature provider"
        responses.add(responses.GET, url, body=pdf_content, status=200)
        signature_backend = get_signature_backend()

        pdf_data = signature_backend.get_signed_file(reference_id)

        self.assertEqual(pdf_data, pdf_content)

    @responses.activate
    def test_backend_lex_persona_get_signed_file_fails_when_reference_does_not_exist(
        self,
    ):
        """
        When we request to the signature provider that we want to retrieve a signed file
        through a specific signature backend reference, if it does not exist, it should return an
        exception.
        """
        reference_id = "wlf_dummy_id_must_fail"
        url = f"https://lex_persona.test01.com/api/workflows/{reference_id}/downloadDocuments"
        expected_failing_response = {
            "status": 404,
            "error": "Not Found",
            "message": "The specified workflow can not be found.",
            "requestId": "796f8fe0-1934599",
            "code": "WorkflowNotFound",
        }
        responses.add(responses.GET, url, json=expected_failing_response, status=404)
        signature_backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            signature_backend.get_signed_file(reference_id)

        self.assertEqual(
            str(context.exception),
            f"['Lex Persona: The specified reference can not be found : {reference_id}.']",
        )
