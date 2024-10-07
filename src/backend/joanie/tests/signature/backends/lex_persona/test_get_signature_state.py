"""Test suite for the Lex Persona Signature Backend `get_signature_state`"""

from http import HTTPStatus

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
    JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS=60 * 60 * 24 * 15,
    JOANIE_SIGNATURE_TIMEOUT=3,
)
class LexPersonaBackendGetSignatureState(TestCase):
    """
    Test suite for `get_signature_state`
    """

    @responses.activate
    def test_backend_lex_persona_get_signature_state_when_nobody_has_signed_yet(
        self,
    ):
        """
        Test that the method `get_signature_state` return that nobody has signed the document.
        It should return the value False for the student and the organization in the dictionnary.
        """
        backend = get_signature_backend()
        workflow_id = "wfl_fake_id"
        api_url = f"https://lex_persona.test01.com/api/workflows/{workflow_id}/"
        response = {
            "allowConsolidation": True,
            "allowedCoManagerUsers": [],
            "coManagerNotifiedEvents": [],
            "created": 1726242320013,
            "currentRecipientEmails": ["johndoe@acme.fr"],
            "currentRecipientUsers": [],
            "description": "1 rue de l'exemple, 75000 Paris",
            "email": "johndoes@acme.fr",
            "firstName": "John",
            "groupId": "grp_fake_id",
            "id": workflow_id,
            "lastName": "Does",
            "logs": [],
            "name": "Test workflow signature",
            "notifiedEvents": [
                "recipientFinished",
                "workflowStopped",
                "workflowFinished",
            ],
            "progress": 0,
            "started": 1726242331317,
            "steps": [
                {
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                    "id": "stp_fake_id",
                    "invitePeriod": 86400000,
                    "isFinished": False,
                    "isStarted": True,
                    "logs": [
                        {"created": 1726242331317, "operation": "start"},
                        {
                            "created": 1726242331317,
                            "operation": "notifyWorkflowStarted",
                        },
                    ],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "consentPageId": "cop_fake_id",
                            "country": "FR",
                            "email": "johndoe@acme.org",
                            "firstName": "John Doe",
                            "lastName": ".",
                            "phoneNumber": "",
                            "preferredLocale": "fr",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": 86400000,
                },
                {
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                    "id": "stp_fake_id",
                    "invitePeriod": 86400000,
                    "isFinished": False,
                    "isStarted": False,
                    "logs": [],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "consentPageId": "cop_fake_id",
                            "country": "FR",
                            "email": "janedoe@acme.org",
                            "firstName": "Jane Doe",
                            "lastName": ".",
                            "phoneNumber": "",
                            "preferredLocale": "fr",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": 86400000,
                },
            ],
            "tenantId": "ten_fake_id",
            "updated": 1726242331422,
            "userId": "usr_fake_id",
            "viewAuthorizedGroups": ["grp_fake_id"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "started",
        }
        responses.add(
            responses.GET,
            api_url,
            json=response,
            status=HTTPStatus.OK,
        )

        signature_state = backend.get_signature_state(reference_id=workflow_id)

        self.assertEqual(signature_state, {"student": False, "organization": False})

    @responses.activate
    def test_backend_lex_persona_get_signature_state_when_one_person_has_signed(
        self,
    ):
        """
        Test that the method `get_signature_state` that the student has signed the document.
        It should return the value True for the student and False for the organization
        in the dictionary.
        """
        backend = get_signature_backend()
        workflow_id = "wfl_fake_id"
        api_url = f"https://lex_persona.test01.com/api/workflows/{workflow_id}/"

        response = {
            "allowConsolidation": True,
            "allowedCoManagerUsers": [],
            "coManagerNotifiedEvents": [],
            "created": 1726235653238,
            "currentRecipientEmails": [],
            "currentRecipientUsers": [],
            "description": "1 rue de l'exemple, 75000 Paris",
            "email": "johndoe@acme.org",
            "firstName": "John",
            "groupId": "grp_fake_id",
            "id": workflow_id,
            "lastName": "Doe",
            "logs": [],
            "name": "Test Workflow Signature",
            "notifiedEvents": [
                "recipientFinished",
                "workflowStopped",
                "workflowFinished",
            ],
            "progress": 50,
            "started": 1726235671708,
            "steps": [
                {
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                    "id": "stp_fake_id",
                    "invitePeriod": 86400000,
                    "isFinished": True,
                    "isStarted": True,
                    "logs": [
                        {"created": 1726235671708, "operation": "start"},
                        {
                            "created": 1726235671708,
                            "operation": "notifyWorkflowStarted",
                        },
                        {
                            "created": 1726235727060,
                            "evidenceId": "evi_serversealingiframe_fake_id",
                            "operation": "sign",
                            "recipientEmail": "johndoes@acme.org",
                        },
                        {
                            "created": 1726235727060,
                            "operation": "notifyRecipientFinished",
                            "recipientEmail": "johndoes@acme.org",
                        },
                    ],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "consentPageId": "cop_fake_id",
                            "country": "FR",
                            "email": "johndoes@acme.org",
                            "firstName": "John Doe",
                            "lastName": ".",
                            "phoneNumber": "",
                            "preferredLocale": "fr",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": 86400000,
                },
                {
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                    "id": "stp_fake_id",
                    "invitePeriod": 86400000,
                    "isFinished": False,
                    "isStarted": True,
                    "logs": [],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "consentPageId": "cop_fake_id",
                            "country": "FR",
                            "email": "janedoe@acme.fr",
                            "firstName": "Jane Doe",
                            "lastName": ".",
                            "phoneNumber": "",
                            "preferredLocale": "fr",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": 86400000,
                },
            ],
            "tenantId": "ten_fake_id",
            "updated": 1726237384491,
            "userId": "usr_fake_id",
            "viewAuthorizedGroups": ["grp_fake_id"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "started",
        }

        responses.add(
            responses.GET,
            api_url,
            json=response,
            status=HTTPStatus.OK,
        )

        signature_state = backend.get_signature_state(reference_id=workflow_id)

        self.assertEqual(signature_state, {"student": True, "organization": False})

    @responses.activate
    def test_backend_lex_persona_get_signature_state_all_signatories_have_signed(
        self,
    ):
        """
        Test that the method `get_signature_state` that both have signed the document.
        It should return the value True for the student and the organization in the dictionary.
        """
        backend = get_signature_backend()
        workflow_id = "wfl_fake_id"
        api_url = f"https://lex_persona.test01.com/api/workflows/{workflow_id}/"
        response = {
            "allowConsolidation": True,
            "allowedCoManagerUsers": [],
            "coManagerNotifiedEvents": [],
            "created": 1726235653238,
            "currentRecipientEmails": [],
            "currentRecipientUsers": [],
            "description": "1 rue de l'exemple, 75000 Paris",
            "email": "johndoes@acme.org",
            "firstName": "John",
            "groupId": "grp_fake_id",
            "id": "wfl_fake_id",
            "lastName": "Does",
            "logs": [],
            "name": "Test workflow signature",
            "notifiedEvents": [
                "recipientFinished",
                "workflowStopped",
                "workflowFinished",
            ],
            "progress": 100,
            "started": 1726235671708,
            "steps": [
                {
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                    "id": "stp_fake_id",
                    "invitePeriod": 86400000,
                    "isFinished": True,
                    "isStarted": True,
                    "logs": [
                        {"created": 1726235671708, "operation": "start"},
                        {
                            "created": 1726235671708,
                            "operation": "notifyWorkflowStarted",
                        },
                        {
                            "created": 1726235727060,
                            "evidenceId": "evi_serversealingiframe_fake_id",
                            "operation": "sign",
                            "recipientEmail": "johndoe@acme.org",
                        },
                        {
                            "created": 1726235727060,
                            "operation": "notifyRecipientFinished",
                            "recipientEmail": "johndoe@acme.org",
                        },
                    ],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "consentPageId": "cop_fake_id",
                            "country": "FR",
                            "email": "johndoe@acme.org",
                            "firstName": "John Doe",
                            "lastName": ".",
                            "phoneNumber": "",
                            "preferredLocale": "fr",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": 86400000,
                },
                {
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                    "id": "stp_fake_id",
                    "invitePeriod": 86400000,
                    "isFinished": True,
                    "isStarted": True,
                    "logs": [
                        {"created": 1726235727082, "operation": "start"},
                        {
                            "created": 1726237384315,
                            "evidenceId": "evi_serversealingiframe_fake_id",
                            "operation": "sign",
                            "recipientEmail": "janedoe@acme.org",
                        },
                        {
                            "created": 1726237384315,
                            "operation": "notifyRecipientFinished",
                            "recipientEmail": "janedoe@acme.org",
                        },
                        {
                            "created": 1726237384315,
                            "operation": "notifyWorkflowFinished",
                        },
                    ],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "consentPageId": "cop_fake_id",
                            "country": "FR",
                            "email": "janedoe@acme.org",
                            "firstName": "Jane Doe",
                            "lastName": ".",
                            "phoneNumber": "",
                            "preferredLocale": "fr",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": 86400000,
                },
            ],
            "tenantId": "ten_fake_id",
            "updated": 1726237384491,
            "userId": "usr_fake_id",
            "viewAuthorizedGroups": ["grp_fake_id"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "finished",
        }

        responses.add(
            responses.GET,
            api_url,
            json=response,
            status=HTTPStatus.OK,
        )

        signature_state = backend.get_signature_state(reference_id=workflow_id)

        self.assertEqual(signature_state, {"student": True, "organization": True})

    @responses.activate
    def test_backend_lex_persona_get_signature_state_returns_not_found(
        self,
    ):
        """
        Test that the method `get_signature_state` should return a status code
        NOT_FOUND (404) because the reference does not exist at the signature provider.
        """
        backend = get_signature_backend()
        workflow_id = "wfl_fake_id_not_exist"
        api_url = f"https://lex_persona.test01.com/api/workflows/{workflow_id}/"
        response = {
            "status": 404,
            "error": "Not Found",
            "message": "The specified workflow can not be found.",
            "requestId": "2a72",
            "code": "WorkflowNotFound",
        }

        responses.add(
            responses.GET,
            api_url,
            json=response,
            status=HTTPStatus.NOT_FOUND,
        )

        with self.assertRaises(exceptions.SignatureProcedureNotFound) as context:
            backend.get_signature_state(reference_id=workflow_id)

        self.assertEqual(
            str(context.exception),
            "Lex Persona: Unable to retrieve the signature procedure the reference "
            "does not exist wfl_fake_id_not_exist",
        )
