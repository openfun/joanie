"""Test suite for `generate_document` utility"""

import textwrap
from io import BytesIO

from django.template.exceptions import TemplateDoesNotExist
from django.test import TestCase

import markdown
from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core.utils import issuers


class UtilsGenerateDocumentTestCase(TestCase):
    """Test suite for `generate_document` utility"""

    def test_utils_issuers_generate_document(self):
        """
        Generate document should create the pdf document when the given name
        in order to reach the .html and .css file exist.
        If it can't find the name of the files, it raises en error.
        """
        markdown_content = """
        ## Article 1
        The student must have a computer to follow the course

        ## Article 2
        The student and the organization are tied down to this contract

        ## Article 3
        The student has paid in advance the whole course before the start
        """
        markdown_terms_and_conditions = """
        ## Terms and conditions
        Here are the terms and conditions of the current contract
        """

        body_content = markdown.markdown(textwrap.dedent(markdown_content))
        terms_and_conditions_content = markdown.markdown(
            textwrap.dedent(markdown_terms_and_conditions)
        )
        context = {
            "contract": {
                "body": body_content,
                "terms_and_conditions": terms_and_conditions_content,
                "title": "Contract Definition",
                "description": "This is the contract definition",
            },
            "course": {
                "name": "Some course name",
            },
            "student": {
                "name": "John Doe",
                "address": {
                    "address": "1 Rue de L'Exemple",
                    "city": "Paris",
                    "country": "FR",
                    "last_name": "Doe",
                    "first_name": "John",
                    "postcode": "75000",
                    "is_main": True,
                    "title": "Office",
                },
            },
            "organization": {
                "logo": "cover.png",
                "name": "Academic Course Provider",
                "signature": "organization_signature.png",
            },
        }

        document_text = pdf_extract_text(
            BytesIO(
                issuers.generate_document(
                    name="contract_definition",
                    context=context,
                )
            )
        ).replace("\n", "")

        self.assertIn("Contract Definition", document_text)
        self.assertIn("John Doe", document_text)
        self.assertIn("1 Rue de L'Exemple, 75000 Paris (FR)", document_text)
        self.assertIn("must have a computer", document_text)
        self.assertIn("student and the organization are tied", document_text)
        self.assertIn("are the terms and conditions of the", document_text)
        self.assertIn("[SignatureField#1]", document_text)

        with self.assertRaises(TemplateDoesNotExist) as context:
            issuers.generate_document(name="convention", context=context)
        self.assertEqual(
            str(context.exception),
            "issuers/convention.html",
        )
