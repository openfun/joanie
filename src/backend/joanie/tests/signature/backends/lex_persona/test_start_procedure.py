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
    def test_backend_lex_persona_start_workflowstatus(self):
        """
        When updating an existing signature procedure to start, it should change its
        'workflowStatus' to 'started'.
        """
        reference_id = "wfl_id_fake"
        api_url = f"https://lex_persona.test01.com/api/workflows/{reference_id}"
        expected_response_data = {
            "created": 1696238245608,
            "currentRecipientEmails": [],
            "currentRecipientUsers": [],
            "description": "1 rue de l'exemple, 75000 Paris",
            "email": "johndoe@example.fr",
            "firstName": "John",
            "groupId": "grp_id_fake",
            "id": "wfl_id_fake",
            "lastName": "Doe",
            "logs": [],
            "name": "Heavy Duty Wool Watch",
            "notifiedEvents": [
                "recipientRefused",
                "recipientFinished",
                "workflowStopped",
                "workflowFinished",
            ],
            "progress": 0,
            "steps": [
                {
                    "allowComments": True,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": True,
                    "id": "stp_J5gCgaRRY4NHtbGs474WjMkA",
                    "invitePeriod": None,
                    "isFinished": False,
                    "isStarted": False,
                    "logs": [],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "consentPageId": "cop_id_fake",
                            "country": "FR",
                            "email": "johnnydoe@example.fr",
                            "firstName": "Johnny",
                            "lastName": "Doe",
                            "preferredLocale": "fr",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": 86400000,
                }
            ],
            "tenantId": "ten_id_fake",
            "updated": 1696238262735,
            "userId": "usr_id_fake",
            "viewAuthorizedGroups": ["grp_id_fake"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "started",
        }
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
            "Cannot start the signature procedure with signature reference",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "PATCH")
