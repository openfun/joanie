"""Test suite for the Lex Persona Signature Backend upload_file_to_workflow"""
from django.test import TestCase
from django.test.utils import override_settings

import responses

from joanie.signature import exceptions
from joanie.signature.backends import get_signature_backend

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
class LexPersonaBackendUploadFileToWorkflowTestCase(TestCase):
    """Test suite for Lex Persona Signature provider Backend upload_file_to_workflow."""

    @responses.activate
    def test_backend_lex_persona_upload_file_to_workflow(self):
        """
        When uploading the file to an existing signature procedure, it should return the hash of
        the file when it suceeds.
        """
        workflow_id = "wfl_id_fake"
        api_url = (
            f"https://lex_persona.test01.com/api/workflows/{workflow_id}"
            "/parts?createDocuments=true&ignoreAttachments=false"
            "&signatureProfileId=sip_profile_id_fake&unzip=false&pdf2pdfa=auto"
        )
        expected_response_data = {
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
        file_bytes = b"Some fake content"
        backend = get_signature_backend()

        responses.add(responses.POST, api_url, status=200, json=expected_response_data)
        file_hash = backend._upload_file_to_workflow(file_bytes, workflow_id)

        self.assertEqual(file_hash, expected_response_data["parts"][0].get("hash"))
        self.assertEqual(
            expected_response_data.get("documents")[0].get("workflowId"),
            workflow_id,
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertIsNotNone(responses.calls[0].request.body)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")

    @responses.activate
    def test_backend_lex_persona_upload_file_failed(self):
        """
        When uploading a file to the signature procedure fails, it should raise the exception
        Upload Document Failed.
        """
        api_url = (
            "https://lex_persona.test01.com/api/workflows/wfl_id_fake"
            "/parts?createDocuments=true&ignoreAttachments=false"
            "&signatureProfileId=sip_profile_id_fake&unzip=false&pdf2pdfa=auto"
        )
        backend = get_signature_backend()

        responses.add(
            responses.POST,
            api_url,
            status=403,
            json={
                "status": 403,
                "error": "Forbidden",
                "message": "The specified signature profile is not allowed for this document.",
                "requestId": "b609eeba-546171",
                "code": "SignatureProfileNotAllowed",
                "logId": "log_GLDiyBejx5foCZ9VgLYSkkX6",
            },
        )
        with self.assertRaises(exceptions.UploadFileFailed) as context:
            backend._upload_file_to_workflow(b"not_a_file", "wfl_id_fake")

        self.assertEqual(
            str(context.exception),
            (
                "Lex Persona: Cannot upload the file to the signature provider with"
                " the signature reference."
            ),
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "POST")
