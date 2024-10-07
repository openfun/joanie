"""Test suite for the Lex Persona Signature Backend delete_signing_procedure"""

from http import HTTPStatus

from django.test import TestCase
from django.test.utils import override_settings

import responses
from requests.exceptions import ReadTimeout

from joanie.core.exceptions import BackendTimeout
from joanie.signature import exceptions
from joanie.signature.backends import get_signature_backend
from joanie.tests.base import BaseLogMixinTestCase

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
class LexPersonaBackendTestCase(TestCase, BaseLogMixinTestCase):
    """Test suite for Lex Persona Signature provider Backend delete_signing_procedure."""

    @responses.activate
    def test_backend_lex_persona_delete_signing_procedure(self):
        """
        When deleting a signature procedure with its signature backend reference that exists,
        it should change the 'workflowStatus' to 'stopped'.
        """
        api_url = "https://lex_persona.test01.com/api/workflows/wfl_id_fake"
        expected_response_data = get_expected_workflow_payload("stopped")
        backend = get_signature_backend()

        responses.add(
            responses.DELETE,
            api_url,
            json=expected_response_data,
            status=HTTPStatus.OK,
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
        with self.assertRaises(exceptions.DeleteSignatureProcedureFailed) as context:
            backend.delete_signing_procedure(reference_id="wfl_id_fake")

        self.assertEqual(
            str(context.exception),
            (
                "Lex Persona: Unable to delete the signature procedure the reference "
                "does not exist wfl_id_fake"
            ),
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "DELETE")

    @responses.activate
    def test_backend_lex_persona_delete_signing_procedure_reaches_timeout(self):
        """
        When deleting a signature procedure requests reaches a `ReadTimeout`, it should raise
        a `BackendTimeOut` with the error message mentioning that it takes a while for the
        signature provider to delete the reference on their side. We should also see log messages
        that mentions the reference being deleted.
        """
        backend = get_signature_backend()

        responses.add(
            responses.DELETE,
            "https://lex_persona.test01.com/api/workflows/wfl_id_fake",
            body=ReadTimeout(
                "Deletion request is taking longer than expected for reference: wfl_id_fake"
            ),
        )

        with self.assertRaises(BackendTimeout) as context:
            with self.assertLogs("joanie") as logger:
                backend.delete_signing_procedure(reference_id="wfl_id_fake")

        self.assertEqual(
            str(context.exception),
            "Deletion request is taking longer than expected for reference: wfl_id_fake",
        )

        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    "Deletion request is taking longer than expected for reference: wfl_id_fake",
                    {
                        "signature_backend_reference": str,
                    },
                )
            ],
        )
