"""Lex Persona backend test for submit_for_signature."""

from http import HTTPStatus

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings

import responses

from joanie.core import enums, factories
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
class LexPersonaBackendSubmitForSignatureTestCase(TestCase):
    """Lex Persona backend test for submit_for_signature."""

    # pylint: disable=too-many-locals,unexpected-keyword-arg,no-value-for-parameter
    @responses.activate(assert_all_requests_are_fired=True)
    def test_submit_for_signature_success(self):
        """valid test submit for signature"""
        user = factories.UserFactory(email="johnnydo@example.fr")
        order = factories.OrderFactory(owner=user, state=enums.ORDER_STATE_VALIDATED)
        accesses = factories.UserOrganizationAccessFactory.create_batch(
            3, organization=order.organization, role="owner"
        )
        file_bytes = b"Some fake content"
        workflow_id = "wfl_id_fake"
        title = "Contract Definition"

        ## Create workflow
        create_workflow_api_url = (
            "https://lex_persona.test01.com/api/users/usr_id_fake/workflows"
        )
        create_workflow_response_data = {
            "created": 1696238245608,
            "currentRecipientEmails": [],
            "currentRecipientUsers": [],
            "description": "Contract Definition",
            "email": order.owner.email,
            "firstName": order.owner.first_name,
            "groupId": "grp_id_fake",
            "id": workflow_id,
            "lastName": ".",
            "logs": [],
            "name": "Contract Definition",
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
                            "lastName": ".",
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
            "updated": 1696238245608,
            "userId": "usr_id_fake",
            "viewAuthorizedGroups": ["grp_id_fake"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "stopped",
        }
        responses.add(
            responses.POST,
            create_workflow_api_url,
            status=HTTPStatus.OK,
            json=create_workflow_response_data,
            match=[
                responses.matchers.header_matcher(
                    {
                        "Authorization": "Bearer token_id_fake",
                    },
                ),
                responses.matchers.json_params_matcher(
                    {
                        "name": title,
                        "description": title,
                        "steps": [
                            {
                                "stepType": "signature",
                                "recipients": [
                                    {
                                        "consentPageId": "cop_id_fake",
                                        "country": order.main_invoice.recipient_address.country.code.upper(),  # pylint: disable=line-too-long
                                        "email": user.email,
                                        "firstName": user.first_name,
                                        "lastName": ".",
                                        "preferred_locale": user.language.lower(),
                                    }
                                ],
                                "requiredRecipients": 1,
                                "validityPeriod": (
                                    settings.JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS
                                    * 1000
                                ),
                                "invitePeriod": None,
                                "maxInvites": 0,
                                "sendDownloadLink": True,
                                "allowComments": False,
                                "hideAttachments": False,
                                "hideWorkflowRecipients": False,
                            },
                            {
                                "stepType": "signature",
                                "recipients": [
                                    {
                                        "email": access.user.email,
                                        "firstName": access.user.first_name,
                                        "lastName": ".",
                                        "country": order.organization.country.code.upper(),
                                        "preferred_locale": access.user.language.lower(),
                                        "consentPageId": "cop_id_fake",
                                    }
                                    for access in reversed(accesses)
                                ],
                                "requiredRecipients": 1,
                                "validityPeriod": (
                                    settings.JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS
                                    * 1000
                                ),
                                "invitePeriod": None,
                                "maxInvites": 0,
                                "sendDownloadLink": True,
                                "allowComments": False,
                                "hideAttachments": False,
                                "hideWorkflowRecipients": False,
                            },
                        ],
                        "notifiedEvents": [
                            "recipientRefused",
                            "recipientFinished",
                            "workflowFinished",
                        ],
                        "watchers": [],
                    }
                ),
            ],
        )

        ## upload file to workflow
        upload_file_api_url = (
            f"https://lex_persona.test01.com/api/workflows/{workflow_id}"
            "/parts?createDocuments=true&ignoreAttachments=false"
            "&signatureProfileId=sip_profile_id_fake&unzip=false&pdf2pdfa=auto"
        )
        upload_file_response_data = {
            "documents": [
                {
                    "created": 1696238255558,
                    "groupId": "grp_id_fake",
                    "id": "doc_id_fake",
                    "parts": [
                        {
                            "contentType": "application/pdf",
                            "filename": "contract_definition.pdf",
                            "hash": "wpTD3tstfdt9XfuFK+sv4/y6fv3lx3hwZ2gjQ2DBrxs=",
                            "size": 123616,
                        }
                    ],
                    "signatureProfileId": "sip_profile_id_fake",
                    "tenantId": "ten_id_fake",
                    "updated": 1696238255558,
                    "userId": "usr_id_fake",
                    "viewAuthorizedGroups": ["grp_id_fake"],
                    "viewAuthorizedUsers": [],
                    "workflowId": "wfl_id_fake",
                    "workflowName": "Heavy Duty Wool Watch",
                }
            ],
            "ignoredAttachments": 0,
            "parts": [
                {
                    "contentType": "application/pdf",
                    "filename": "contract_definition.pdf",
                    "hash": "wpTD3tstfdt9XfuFK+sv4/y6fv3lx3hwZ2gjQ2DBrxs=",
                    "size": 123616,
                }
            ],
        }
        responses.add(
            responses.POST,
            upload_file_api_url,
            status=HTTPStatus.OK,
            json=upload_file_response_data,
            match=[
                responses.matchers.header_matcher(
                    {
                        "Authorization": "Bearer token_id_fake",
                    },
                ),
                responses.matchers.multipart_matcher(
                    {
                        "file1": (
                            "contract_definition.pdf",
                            file_bytes,
                            "application/pdf",
                        ),
                    },
                ),
            ],
        )

        ## Start procedure
        start_procedure_api_url = (
            f"https://lex_persona.test01.com/api/workflows/{workflow_id}"
        )
        start_procedure_response_data = get_expected_workflow_payload("started")
        responses.add(
            responses.PATCH,
            start_procedure_api_url,
            status=HTTPStatus.OK,
            json=start_procedure_response_data,
            match=[
                responses.matchers.header_matcher(
                    {
                        "Authorization": "Bearer token_id_fake",
                    },
                ),
                responses.matchers.json_params_matcher(
                    {
                        "workflowStatus": "started",
                    }
                ),
            ],
        )

        lex_persona_backend = get_signature_backend()

        reference_id, file_hash = lex_persona_backend.submit_for_signature(
            title=title, file_bytes=file_bytes, order=order
        )

        self.assertEqual(workflow_id, reference_id)
        self.assertEqual(file_hash, upload_file_response_data["parts"][0].get("hash"))

    @responses.activate
    def test_submit_for_signature_create_worklow_failed(self):
        """
        If some required values in the payload are missing when creating the signature procedure,
        it will raise the exception Create Workflow Signature Failed.
        """

        user = factories.UserFactory(email="johnnydo@example.fr")
        order = factories.OrderFactory(owner=user, state=enums.ORDER_STATE_VALIDATED)
        factories.UserOrganizationAccessFactory.create_batch(
            3, organization=order.organization, role="owner"
        )
        file_bytes = b"Some fake content"

        ## Create workflow
        create_workflow_api_url = (
            "https://lex_persona.test01.com/api/users/usr_id_fake/workflows"
        )

        responses.add(
            responses.POST,
            create_workflow_api_url,
            status=HTTPStatus.BAD_REQUEST,
            json={
                "status": 400,
                "error": "Bad Request",
                "message": "A recipient in the request is missing identity information.",
                "requestId": "8cecebbd-235860",
                "code": "RecipientInfoMissing",
                "logId": "log_8vxLbfT6i8TtEZ2mu8wN9z3p",
            },
        )

        lex_persona_backend = get_signature_backend()

        with self.assertRaises(exceptions.CreateSignatureProcedureFailed) as context:
            lex_persona_backend.submit_for_signature(
                title="Contract Definition", file_bytes=file_bytes, order=order
            )

        self.assertEqual(
            str(context.exception),
            "Lex Persona: Cannot create a signature procedure.",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, create_workflow_api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")

    @responses.activate
    def test_submit_for_signature_upload_file_failed(self):
        """
        When uploading a file to the signature procedure fails, it should raise the exception
        Upload Document Failed.
        """
        user = factories.UserFactory(email="johnnydo@example.fr")
        order = factories.OrderFactory(owner=user, state=enums.ORDER_STATE_VALIDATED)
        factories.UserOrganizationAccessFactory.create_batch(
            3, organization=order.organization, role="owner"
        )
        file_bytes = b"Some fake content"
        workflow_id = "wfl_id_fake"

        ## Create workflow
        create_workflow_api_url = (
            "https://lex_persona.test01.com/api/users/usr_id_fake/workflows"
        )
        create_workflow_response_data = {
            "created": 1696238245608,
            "currentRecipientEmails": [],
            "currentRecipientUsers": [],
            "description": "Contract Definition",
            "email": order.owner.email,
            "firstName": order.owner.first_name,
            "groupId": "grp_id_fake",
            "id": workflow_id,
            "lastName": ".",
            "logs": [],
            "name": "Contract Definition",
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
            "updated": 1696238245608,
            "userId": "usr_id_fake",
            "viewAuthorizedGroups": ["grp_id_fake"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "stopped",
        }
        responses.add(
            responses.POST,
            create_workflow_api_url,
            status=HTTPStatus.OK,
            json=create_workflow_response_data,
        )

        ## Upload file
        upload_file_api_url = (
            f"https://lex_persona.test01.com/api/workflows/{workflow_id}"
            "/parts?createDocuments=true&ignoreAttachments=false"
            "&signatureProfileId=sip_profile_id_fake&unzip=false&pdf2pdfa=auto"
        )
        responses.add(
            responses.POST,
            upload_file_api_url,
            status=HTTPStatus.FORBIDDEN,
            json={
                "status": 403,
                "error": "Forbidden",
                "message": "The specified signature profile is not allowed for this document.",
                "requestId": "b609eeba-546171",
                "code": "SignatureProfileNotAllowed",
                "logId": "log_GLDiyBejx5foCZ9VgLYSkkX6",
            },
        )

        lex_persona_backend = get_signature_backend()
        with self.assertRaises(exceptions.UploadFileFailed) as context:
            lex_persona_backend.submit_for_signature(
                title="Contract Definition", file_bytes=file_bytes, order=order
            )

        self.assertEqual(
            str(context.exception),
            (
                "Lex Persona: Cannot upload the file to the signature provider with"
                " the signature reference."
            ),
        )
        self.assertEqual(len(responses.calls), 2)

        # First create workflow
        self.assertEqual(responses.calls[0].request.url, create_workflow_api_url)
        self.assertIsNotNone(responses.calls[0].request.body)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")

        ## Upload file failure
        self.assertEqual(responses.calls[1].request.url, upload_file_api_url)
        self.assertEqual(
            responses.calls[1].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[1].request.method, "POST")

    @responses.activate
    def test_submit_for_signature_start_procedure_failed(self):
        """
        When starting a signature procedure that does not exist, it should
        raise the exception Start Signature Procedure Failed.
        """
        user = factories.UserFactory(email="johnnydo@example.fr")
        order = factories.OrderFactory(owner=user, state=enums.ORDER_STATE_VALIDATED)
        factories.UserOrganizationAccessFactory.create_batch(
            3, organization=order.organization, role="owner"
        )
        file_bytes = b"Some fake content"
        workflow_id = "wfl_id_fake"
        lex_persona_backend = get_signature_backend()

        ## Create workflow
        create_workflow_api_url = (
            "https://lex_persona.test01.com/api/users/usr_id_fake/workflows"
        )
        create_workflow_response_data = {
            "created": 1696238245608,
            "currentRecipientEmails": [],
            "currentRecipientUsers": [],
            "description": "Contract Definition",
            "email": order.owner.email,
            "firstName": order.owner.first_name,
            "groupId": "grp_id_fake",
            "id": workflow_id,
            "lastName": ".",
            "logs": [],
            "name": "Contract Definition",
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
            "updated": 1696238245608,
            "userId": "usr_id_fake",
            "viewAuthorizedGroups": ["grp_id_fake"],
            "viewAuthorizedUsers": [],
            "watchers": [],
            "workflowStatus": "stopped",
        }
        responses.add(
            responses.POST,
            create_workflow_api_url,
            status=HTTPStatus.OK,
            json=create_workflow_response_data,
        )

        ## upload file to workflow

        upload_file_api_url = (
            f"https://lex_persona.test01.com/api/workflows/{workflow_id}"
            "/parts?createDocuments=true&ignoreAttachments=false"
            "&signatureProfileId=sip_profile_id_fake&unzip=false&pdf2pdfa=auto"
        )
        upload_file_response_data = {
            "documents": [
                {
                    "created": 1696238255558,
                    "groupId": "grp_id_fake",
                    "id": "doc_id_fake",
                    "parts": [
                        {
                            "contentType": "application/pdf",
                            "filename": "contract_definition.pdf",
                            "hash": "wpTD3tstfdt9XfuFK+sv4/y6fv3lx3hwZ2gjQ2DBrxs=",
                            "size": 123616,
                        }
                    ],
                    "signatureProfileId": "sip_profile_id_fake",
                    "tenantId": "ten_id_fake",
                    "updated": 1696238255558,
                    "userId": "usr_id_fake",
                    "viewAuthorizedGroups": ["grp_id_fake"],
                    "viewAuthorizedUsers": [],
                    "workflowId": "wfl_id_fake",
                    "workflowName": "Heavy Duty Wool Watch",
                }
            ],
            "ignoredAttachments": 0,
            "parts": [
                {
                    "contentType": "application/pdf",
                    "filename": "contract_definition.pdf",
                    "hash": "wpTD3tstfdt9XfuFK+sv4/y6fv3lx3hwZ2gjQ2DBrxs=",
                    "size": 123616,
                }
            ],
        }
        responses.add(
            responses.POST,
            upload_file_api_url,
            status=HTTPStatus.OK,
            json=upload_file_response_data,
        )

        ## Start procedure
        start_procedure_api_url = (
            f"https://lex_persona.test01.com/api/workflows/{workflow_id}"
        )

        responses.add(
            responses.PATCH,
            start_procedure_api_url,
            json={"workflowStatus": "started"},
            status=HTTPStatus.BAD_REQUEST,
        )
        with self.assertRaises(exceptions.StartSignatureProcedureFailed) as context:
            lex_persona_backend.submit_for_signature(
                title="Contract Definition", file_bytes=file_bytes, order=order
            )

        self.assertEqual(
            str(context.exception),
            "Lex Persona: Cannot start the signature procedure with signature reference",
        )

        self.assertEqual(len(responses.calls), 3)

        # First create workflow
        self.assertEqual(responses.calls[0].request.url, create_workflow_api_url)
        self.assertIsNotNone(responses.calls[0].request.body)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")

        # Second upoad file
        self.assertEqual(responses.calls[1].request.url, upload_file_api_url)
        self.assertIsNotNone(responses.calls[1].request.body)
        self.assertEqual(
            responses.calls[1].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[1].request.method, "POST")

        # Third start procedure failure
        self.assertEqual(responses.calls[2].request.url, start_procedure_api_url)
        self.assertEqual(
            responses.calls[2].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[2].request.method, "PATCH")

    def test_submit_for_signature_create_worklow_failed_because_no_organization_owners_set(
        self,
    ):
        """
        When attempting to create a signature procedure and the organization does not have any
        members with the 'owner' role, the signature procedure creation should be prevented,
        and an error must be raised.
        """
        user = factories.UserFactory(email="johnnydo@example.fr")
        order = factories.OrderFactory(owner=user, state=enums.ORDER_STATE_VALIDATED)
        file_bytes = b"Some fake content"
        title = "Contract Definition"
        lex_persona_backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            lex_persona_backend.submit_for_signature(
                title=title, file_bytes=file_bytes, order=order
            )

        self.assertEqual(
            str(context.exception.message),
            f"No organization owner found to initiate the signature process for order {order.id}.",
        )
