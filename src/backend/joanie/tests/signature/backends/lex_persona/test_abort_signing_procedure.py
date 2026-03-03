"""Test suite for the Lex Persona Signature Backend `abort_signing_procedure`"""

from http import HTTPStatus

from django.test import TestCase
from django.test.utils import override_settings

import responses

from joanie.signature import exceptions
from joanie.signature.backends import get_signature_backend

from . import get_expected_workflow_payload


@override_settings(
    JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.lex_persona.LexPersonaBackend",
    JOANIE_SIGNATURE_LEXPERSONA_BASE_URL="https://lex_persona.test01.com",
    JOANIE_SIGNATURE_LEXPERSONA_CONSENT_PAGE_ID="cop_id_fake",
    JOANIE_SIGNATURE_LEXPERSONA_SESSION_USER_ID="usr_id_fake",
    JOANIE_SIGNATURE_LEXPERSONA_PROFILE_ID="sip_profile_id_fake",
    JOANIE_SIGNATURE_LEXPERSONA_TOKEN="token_id_fake",
    JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS=60 * 60 * 24 * 15,
    JOANIE_SIGNATURE_TIMEOUT=3,
)
class LexPersonaBackendTestCase(TestCase):
    """Test suite for the Lex Persona Signature Backend `abort_signing_procedure`"""

    @responses.activate
    def test_backend_lex_persona_abort_signing_procedure(self):
        """
        When aborting a signature procedure with its signature backend reference that exists,
        it should change the 'workflowStatus' to 'stopped'.
        """
        api_url = "https://lex_persona.test01.com/api/workflows/wfl_id_fake"
        expected_response_data = get_expected_workflow_payload("stopped")
        backend = get_signature_backend()

        responses.add(
            responses.PATCH,
            api_url,
            json=expected_response_data,
            status=HTTPStatus.OK,
        )
        result = backend.abort_signing_procedure(reference_id="wfl_id_fake")

        self.assertEqual(result, expected_response_data)

        self.assertEqual(result["workflowStatus"], "stopped")
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "PATCH")

    @responses.activate
    def test_backend_lex_persona_abort_signing_procedure_failed(self):
        """
        When aborting a signature procedure with a reference that does not exist or that is
        finished, it should raise Abort Signature Procedure Failed.
        """
        api_url = "https://lex_persona.test01.com/api/workflows/wfl_id_fake"
        backend = get_signature_backend()

        responses.add(
            responses.PATCH,
            api_url,
            status=HTTPStatus.NOT_FOUND,
            json={
                "status": 404,
                "error": "Not Found",
                "message": "The specified workflow can not be found.",
                "requestId": "d44f8bf6-1244051",
                "code": "WorkflowNotFound",
                "logId": "log_F9bcd1sayk7aMWLYSK4QxEVt",
            },
        )
        with self.assertRaises(exceptions.AbortSignatureProcedureFailed) as context:
            backend.abort_signing_procedure(reference_id="wfl_id_fake")

        self.assertTrue(
            "Lex Persona: Cannot abort the signature procedure with signature reference"
            in str(context.exception)
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "PATCH")
