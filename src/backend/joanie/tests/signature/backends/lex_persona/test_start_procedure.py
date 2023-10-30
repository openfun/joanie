"""Test suite for the Lex Persona Signature Backend start_procedure"""
from django.test import TestCase
from django.test.utils import override_settings

import responses

from joanie.signature import exceptions
from joanie.signature.backends import get_signature_backend

from . import get_expected_workflow_payload

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
class LexPersonaBackendStartProcedureTestCase(TestCase):
    """Test suite for Lex Persona Signature provider Backend start_procedure."""

    @responses.activate
    def test_backend_lex_persona_start_workflowstatus(self):
        """
        When updating an existing signature procedure to start, it should change its
        'workflowStatus' to 'started'.
        """
        reference_id = "wfl_id_fake"
        api_url = f"https://lex_persona.test01.com/api/workflows/{reference_id}"
        expected_response_data = get_expected_workflow_payload("started")
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
            "Lex Persona: Cannot start the signature procedure with signature reference",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "PATCH")
