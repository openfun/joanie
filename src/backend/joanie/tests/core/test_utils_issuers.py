"""Tests issuers in utils"""
import textwrap
from io import BytesIO

from django.template.exceptions import TemplateDoesNotExist
from django.test import TestCase

import markdown
from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core.utils import issuers


class UtilsDocumentCreateTestCase(TestCase):
    """Testcase for utility method to generate document"""

    def test_utils_issuer_generate_document(self):
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
        body_content = textwrap.dedent(markdown_content)
        content = markdown.markdown(body_content)
        context = {
            "contract": {
                "body": content,
                "title": "Contract Definition",
            },
            "course": {
                "name": "Some course name",
            },
            "student": {
                "address": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "address": "1 Rue de L'Exemple",
                    "postcode": "75000",
                    "city": "Paris",
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
        self.assertRegex(document_text, r"[SignatureField#1]")
        self.assertRegex(document_text, r"must have a computer")
        self.assertRegex(document_text, r"student and the organization are tied")

        with self.assertRaises(TemplateDoesNotExist) as context:
            issuers.generate_document(name="convention", context=content)
        self.assertEqual(
            str(context.exception),
            "issuers/convention.html",
        )
