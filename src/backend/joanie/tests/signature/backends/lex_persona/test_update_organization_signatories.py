"""Lex Persona backend test for `update_signatories`."""

from http import HTTPStatus

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

import responses

from joanie.core import enums, factories, models
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
class LexPersonaBackendUpdateSignatoriesTestCase(TestCase):
    """Lex Persona backend test for `update_signatories`."""

    # pylint:disable=too-many-locals, duplicate-key, unexpected-keyword-arg, no-value-for-parameter
    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_lex_persona_update_signatories_success(self):
        """
        When update an existing signature procedure to add new signatories to existing workflows,
        it should return, if it succeeds, the signature backend reference that has been updated.
        """
        # Create learner and the order
        user = factories.UserFactory(email="johndoe@example.fr")
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            definition_checksum="1234",
            context="context",
            signature_backend_reference="wfl_id_fake",
            submitted_for_signature_on=timezone.now(),
            student_signed_on=timezone.now(),
            organization_signed_on=None,
        )
        # Create organization user with owner access on the organization
        org_user_1 = factories.UserFactory(email="org_user_1@example.fr")
        factories.UserOrganizationAccessFactory(
            organization=order.organization, role=enums.OWNER, user=org_user_1
        )
        # Create a new organization owner linked to the order
        org_user_2 = factories.UserFactory(email="org_user_2@example.fr")
        factories.UserOrganizationAccessFactory(
            organization=order.organization, role=enums.OWNER, user=org_user_2
        )
        all_organizaiton_accesses_owners = models.OrganizationAccess.objects.filter(
            organization=order.organization, role=enums.OWNER
        )
        # Prepare data for workflow
        workflow_id = "wfl_id_fake"
        title = "Contract Definition"
        validity_period_ms = settings.JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS * 1000
        # Update signature procedure signatories
        update_signatories_procedure_api_url = (
            f"https://lex_persona.test01.com/api/workflows/{workflow_id}/"
        )
        # Pretend that the learner has already signed the file
        update_procedure_response_data = {
            "allowedCoManagerUsers": [],
            "coManagerNotifiedEvents": [],
            "created": 1712739490564,
            "currentRecipientEmails": [
                "org_user_1@example.fr",
                "org_user_2@example.fr",
            ],
            "currentRecipientUsers": [],
            "description": title,
            "email": "user@example.fr",
            "firstName": order.owner.first_name,
            "groupId": "grp_id_fake",
            "id": "wfl_id_fake",
            "jobOperation": "processWorkflow",
            "lastName": ".",
            "logs": [],
            "name": title,
            "notifiedEvents": [
                "recipientRefused",
                "recipientFinished",
                "workflowFinished",
            ],
            "progress": 50,
            "started": 1712739520954,
            "steps": [
                {
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                    "id": "stp_id_fake",
                    "invitePeriod": None,
                    "isFinished": True,
                    "isStarted": True,
                    "logs": [
                        {"created": 1712739520954, "operation": "start"},
                        {
                            "created": 1712739520954,
                            "operation": "notifyWorkflowStarted",
                        },
                        {
                            "created": 1712739520994,
                            "operation": "invite",
                            "recipientEmail": "johndoe@example.fr",
                        },
                        {
                            "created": 1712739579338,
                            "evidenceId": "evi_serversealingiframe_fake_id",
                            "operation": "sign",
                            "recipientEmail": "johndoe@example.fr",
                        },
                        {
                            "created": 1712739579338,
                            "operation": "notifyRecipientFinished",
                            "recipientEmail": "johndoe@example.fr",
                        },
                    ],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "consentPageId": "cop_id_fake",
                            "country": "FR",
                            "email": "johndoe@example.fr",
                            "firstName": "Jon",
                            "lastName": ".",
                            "phoneNumber": "",
                            "preferredLocale": "fr",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": validity_period_ms,
                },
                {
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                    "id": "stp_id_fake",
                    "invitePeriod": None,
                    "isFinished": False,
                    "isStarted": False,
                    "logs": [],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "email": access.user.email,
                            "firstName": access.user.first_name,
                            "lastName": ".",
                            "country": order.organization.country.code.upper(),
                            "preferred_locale": access.user.language.lower(),
                            "consentPageId": "cop_id_fake",
                        }
                        for access in reversed(all_organizaiton_accesses_owners)
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": validity_period_ms,
                },
            ],
            "tenantId": "ten_id_fake",
            "updated": 1712739615424,
            "userId": "usr_id_fake",
            "viewAuthorizedGroups": ["grp_id_fake"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "started",
        }
        responses.add(
            responses.PATCH,
            update_signatories_procedure_api_url,
            status=HTTPStatus.OK,
            json=update_procedure_response_data,
            match=[
                responses.matchers.header_matcher(
                    {
                        "Authorization": "Bearer token_id_fake",
                    },
                ),
                responses.matchers.json_params_matcher(
                    {
                        "steps": [
                            {
                                "stepType": "signature",
                                "recipients": [
                                    {
                                        "email": org_user_2.email,
                                        "firstName": org_user_2.first_name,
                                        "lastName": ".",
                                        "country": order.organization.country.code.upper(),
                                        "preferred_locale": org_user_2.language.lower(),
                                        "consentPageId": "cop_id_fake",
                                    },
                                    {
                                        "email": org_user_1.email,
                                        "firstName": org_user_1.first_name,
                                        "lastName": ".",
                                        "country": order.organization.country.code.upper(),
                                        "preferred_locale": org_user_1.language.lower(),
                                        "consentPageId": "cop_id_fake",
                                    },
                                ],
                                "requiredRecipients": 1,
                                "validityPeriod": validity_period_ms,
                                "invitePeriod": None,
                                "maxInvites": 0,
                                "sendDownloadLink": True,
                                "allowComments": False,
                                "hideAttachments": False,
                                "hideWorkflowRecipients": False,
                            },
                        ],
                    }
                ),
            ],
        )

        lex_persona_backend = get_signature_backend()
        reference_id = lex_persona_backend.update_signatories(
            reference_id=workflow_id,
            all_signatories=False,
        )

        self.assertEqual(workflow_id, reference_id)
        self.assertEqual("started", update_procedure_response_data["workflowStatus"])
        # There should be only 2 signatories from the organization at this moment
        self.assertEqual(
            2, len(update_procedure_response_data["steps"][1]["recipients"])
        )
        # There should still be 2 steps of signature
        self.assertEqual(2, len(update_procedure_response_data["steps"]))

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_lex_persona_update_signatories_with_student_and_organization(self):
        """
        When update an existing signature procedure to add new signatories to existing workflows,
        it should return, if it succeeds, the signature backend reference that has been updated.
        """
        # Create learner and the order
        user = factories.UserFactory(
            email="johndoe@example.fr",
            first_name="John Doe",
            last_name=".",
        )
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            definition_checksum="1234",
            context="context",
            signature_backend_reference="wfl_id_fake",
            submitted_for_signature_on=timezone.now(),
            student_signed_on=None,
            organization_signed_on=None,
        )
        # Create organization user with owner access on the organization
        org_user_1 = factories.UserFactory(email="org_user_1@example.fr")
        factories.UserOrganizationAccessFactory(
            organization=order.organization, role=enums.OWNER, user=org_user_1
        )
        # Create a new organization owner linked to the order
        org_user_2 = factories.UserFactory(email="org_user_2@example.fr")
        factories.UserOrganizationAccessFactory(
            organization=order.organization, role=enums.OWNER, user=org_user_2
        )
        all_organizaiton_accesses_owners = models.OrganizationAccess.objects.filter(
            organization=order.organization, role=enums.OWNER
        )

        # Prepare data for workflow
        validity_period_ms = settings.JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS * 1000
        preferred_locale = order.owner.language
        country = order.main_invoice.recipient_address.country.code
        workflow_id = "wfl_id_fake"
        title = "Contract Definition"

        # Update signature procedure signatories
        update_signatories_procedure_api_url = (
            f"https://lex_persona.test01.com/api/workflows/{workflow_id}/"
        )
        # Pretend that no one has signed the file yet
        update_procedure_response_data = {
            "allowedCoManagerUsers": [],
            "coManagerNotifiedEvents": [],
            "created": 1712739490564,
            "currentRecipientEmails": [
                "johndoe@example.fr",
            ],
            "currentRecipientUsers": [],
            "description": title,
            "email": "user@example.fr",
            "firstName": order.owner.first_name,
            "groupId": "grp_id_fake",
            "id": "wfl_id_fake",
            "jobOperation": "processWorkflow",
            "lastName": ".",
            "logs": [],
            "name": title,
            "notifiedEvents": [
                "recipientRefused",
                "recipientFinished",
                "workflowFinished",
            ],
            "progress": 0,
            "started": 1712739520954,
            "steps": [
                {
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                    "id": "stp_id_fake",
                    "invitePeriod": None,
                    "isFinished": True,
                    "isStarted": True,
                    "logs": [],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "email": "johndoe@example.fr",
                            "firstName": "John Doe",
                            "lastName": ".",
                            "country": country.upper(),
                            "preferredLocale": preferred_locale.lower(),
                            "consentPageId": "cop_id_fake",
                        }
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": validity_period_ms,
                },
                {
                    "allowComments": False,
                    "hideAttachments": False,
                    "hideWorkflowRecipients": False,
                    "id": "stp_id_fake",
                    "invitePeriod": None,
                    "isFinished": False,
                    "isStarted": False,
                    "logs": [],
                    "maxInvites": 0,
                    "recipients": [
                        {
                            "email": access.user.email,
                            "firstName": access.user.first_name,
                            "lastName": ".",
                            "country": order.organization.country.code.upper(),
                            "preferred_locale": access.user.language.lower(),
                            "consentPageId": "cop_id_fake",
                        }
                        for access in reversed(all_organizaiton_accesses_owners)
                    ],
                    "requiredRecipients": 1,
                    "sendDownloadLink": True,
                    "stepType": "signature",
                    "validityPeriod": validity_period_ms,
                },
            ],
            "tenantId": "ten_id_fake",
            "updated": 1712739615424,
            "userId": "usr_id_fake",
            "viewAuthorizedGroups": ["grp_id_fake"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "started",
        }
        responses.add(
            responses.PATCH,
            update_signatories_procedure_api_url,
            status=HTTPStatus.OK,
            json=update_procedure_response_data,
            match=[
                responses.matchers.header_matcher(
                    {
                        "Authorization": "Bearer token_id_fake",
                    },
                ),
                responses.matchers.json_params_matcher(
                    {
                        "steps": [
                            {
                                "allowComments": False,
                                "hideAttachments": False,
                                "hideWorkflowRecipients": False,
                                "invitePeriod": None,
                                "maxInvites": 0,
                                "recipients": [
                                    {
                                        "consentPageId": "cop_id_fake",
                                        "email": "johndoe@example.fr",
                                        "firstName": "John Doe",
                                        "lastName": ".",
                                        "country": country.upper(),
                                        "preferred_locale": preferred_locale.lower(),
                                    }
                                ],
                                "requiredRecipients": 1,
                                "sendDownloadLink": True,
                                "stepType": "signature",
                                "validityPeriod": validity_period_ms,
                            },
                            {
                                "steps": [
                                    {
                                        "allowComments": False,
                                        "hideAttachments": False,
                                        "hideWorkflowRecipients": False,
                                        "invitePeriod": None,
                                        "maxInvites": 0,
                                        "recipients": [
                                            {
                                                "email": org_user_2.email,
                                                "firstName": org_user_2.first_name,
                                                "lastName": ".",
                                                "country": order.organization.country.code.upper(),
                                                "preferred_locale": org_user_2.language.lower(),
                                                "consentPageId": "cop_id_fake",
                                            },
                                            {
                                                "email": org_user_1.email,
                                                "firstName": org_user_1.first_name,
                                                "lastName": ".",
                                                "country": order.organization.country.code.upper(),
                                                "preferred_locale": org_user_1.language.lower(),
                                                "consentPageId": "cop_id_fake",
                                            },
                                        ],
                                        "requiredRecipients": 1,
                                        "sendDownloadLink": True,
                                        "stepType": "signature",
                                        "validityPeriod": validity_period_ms,
                                    }
                                ]
                            },
                        ]
                    }
                ),
            ],
        )

        lex_persona_backend = get_signature_backend()
        reference_id = lex_persona_backend.update_signatories(
            reference_id=workflow_id,
            all_signatories=True,
        )

        self.assertEqual(workflow_id, reference_id)
        self.assertEqual("started", update_procedure_response_data["workflowStatus"])
        # There should be only 1 student in the first step of signatories
        self.assertEqual(
            1, len(update_procedure_response_data["steps"][0]["recipients"])
        )
        # There should be only 2 signatories from the organization at this moment
        self.assertEqual(
            2, len(update_procedure_response_data["steps"][1]["recipients"])
        )
        # There should still be 2 steps of signature
        self.assertEqual(2, len(update_procedure_response_data["steps"]))

    @responses.activate
    def test_backend_lex_persona_update_signatories_with_wrong_reference_id(
        self,
    ):
        """
        If we pass a reference id that is not registered at the signature provider, it should
        raise an error and not let us update the signatories of the given 'reference_id'.
        """
        workflow_id = "fake_wfl_id_fake"
        validity_period_ms = settings.JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS * 1000

        user = factories.UserFactory(email="johndoe@example.fr")
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            definition_checksum="1234",
            context="context",
            signature_backend_reference="fake_wfl_id_fake",
            submitted_for_signature_on=timezone.now(),
            student_signed_on=timezone.now(),
            organization_signed_on=None,
        )

        # Create organization user with owner access on the organization
        org_user_1 = factories.UserFactory(email="org_user_1@example.fr")
        factories.UserOrganizationAccessFactory(
            organization=order.organization, role=enums.OWNER, user=org_user_1
        )
        # Create a new organization owner linked to the order
        org_user_2 = factories.UserFactory(email="org_user_2@example.fr")
        factories.UserOrganizationAccessFactory(
            organization=order.organization, role=enums.OWNER, user=org_user_2
        )

        # Update signature procedure signatories
        update_signatories_procedure_api_url = (
            f"https://lex_persona.test01.com/api/workflows/{workflow_id}/"
        )
        responses.add(
            responses.PATCH,
            update_signatories_procedure_api_url,
            status=HTTPStatus.NOT_FOUND,
            json={
                "status": 404,
                "error": "Not Found",
                "message": "The specified workflow can not be found.",
                "requestId": "32205c11-122154",
                "code": "WorkflowNotFound",
                "logId": "log_id_fake",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "Authorization": "Bearer token_id_fake",
                    },
                ),
                responses.matchers.json_params_matcher(
                    {
                        "steps": [
                            {
                                "stepType": "signature",
                                "recipients": [
                                    {
                                        "email": org_user_2.email,
                                        "firstName": org_user_2.first_name,
                                        "lastName": ".",
                                        "country": order.organization.country.code.upper(),
                                        "preferred_locale": org_user_2.language.lower(),
                                        "consentPageId": "cop_id_fake",
                                    },
                                    {
                                        "email": org_user_1.email,
                                        "firstName": org_user_1.first_name,
                                        "lastName": ".",
                                        "country": order.organization.country.code.upper(),
                                        "preferred_locale": org_user_1.language.lower(),
                                        "consentPageId": "cop_id_fake",
                                    },
                                ],
                                "requiredRecipients": 1,
                                "validityPeriod": validity_period_ms,
                                "invitePeriod": None,
                                "maxInvites": 0,
                                "sendDownloadLink": True,
                                "allowComments": False,
                                "hideAttachments": False,
                                "hideWorkflowRecipients": False,
                            },
                        ],
                    }
                ),
            ],
        )

        lex_persona_backend = get_signature_backend()
        with self.assertRaises(ValidationError) as context:
            lex_persona_backend.update_signatories(
                reference_id=workflow_id,
                all_signatories=False,
            )

        self.assertEqual(
            str(context.exception.message),
            "Lex Persona: Unable to update the signatories for signature procedure with "
            f"the reference {workflow_id}",
        )

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            responses.calls[0].request.url, update_signatories_procedure_api_url
        )
        self.assertEqual(responses.calls[0].request.method, "PATCH")
