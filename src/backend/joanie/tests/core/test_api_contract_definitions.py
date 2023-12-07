"""
Test suite for Contract Definition API.
"""
from io import BytesIO

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class ContractDefinitionApiTest(BaseAPITestCase):
    """
    Test suite for Contract definition API.
    """

    def test_api_contract_definition_preview_template_anonymous(self):
        """
        Anonymous user should not be able to get the contract in PDF bytes.
        """
        contract_definition = factories.ContractDefinitionFactory()

        response = self.client.get(
            f"/api/v1.0/contract_definitions/{str(contract_definition.id)}/preview_template/",
        )

        self.assertEqual(response.status_code, 401)

        content = response.json()
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_contract_definition_preview_template_method_post_should_fail(
        self,
    ):
        """
        Authenticated users should not be able to use the method post.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        contract_definition = factories.ContractDefinitionFactory()
        token = self.get_user_token(user.username)

        response = self.client.post(
            f"/api/v1.0/contract_definitions/{str(contract_definition.id)}/preview_template/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(response, 'Method \\"POST\\" not allowed', status_code=405)

    def test_api_contract_definition_preview_template_method_put_should_fail(
        self,
    ):
        """
        Authenticated users should not be able to use the method put.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        contract_definition = factories.ContractDefinitionFactory()
        token = self.get_user_token(user.username)

        response = self.client.put(
            f"/api/v1.0/contract_definitions/{str(contract_definition.id)}/preview_template/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(response, 'Method \\"PUT\\" not allowed', status_code=405)

    def test_api_contract_definition_preview_template_method_patch_should_fail(
        self,
    ):
        """
        Authenticated users should not be able to use the method patch.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        contract_definition = factories.ContractDefinitionFactory()
        token = self.get_user_token(user.username)

        response = self.client.patch(
            f"/api/v1.0/contract_definitions/{str(contract_definition.id)}/preview_template/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(response, 'Method \\"PATCH\\" not allowed', status_code=405)

    def test_api_contract_definition_preview_template_method_delete_should_fail(
        self,
    ):
        """
        Authenticated users should not be able to use the method delete.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        contract_definition = factories.ContractDefinitionFactory()
        token = self.get_user_token(user.username)

        response = self.client.delete(
            f"/api/v1.0/contract_definitions/{str(contract_definition.id)}/preview_template/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response, 'Method \\"DELETE\\" not allowed', status_code=405
        )

    def test_api_contract_definition_preview_template_success(
        self,
    ):
        """
        Authenticated users should be able to get the PDF in bytes of the contract
        definition to preview the template.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        factories.AddressFactory(owner=user)
        contract_definition = factories.ContractDefinitionFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/contract_definitions/{str(contract_definition.id)}/preview_template/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            'attachment; filename="contract_definition_preview_template.pdf"',
        )

        document_text = pdf_extract_text(BytesIO(b"".join(response.streaming_content)))

        self.assertIn("CONTRACT", document_text)
        self.assertIn("DEFINITION", document_text)
        self.assertIn(
            "This document certifies that the student wants to enroll to the course",
            document_text,
        )
        self.assertIn("Student's signature", document_text)
        self.assertIn("[SignatureField#1]", document_text)
        self.assertIn("Representative's signature", document_text)
        self.assertIn("[SignatureField#2]", document_text)
        self.assertIn(user.first_name, document_text)
        self.assertIn(
            "<STUDENT_ADDRESS_STREET_NAME> <STUDENT_ADDRESS_POSTCODE>,\n<STUDENT_ADDRESS_CITY>.",
            document_text,
        )
