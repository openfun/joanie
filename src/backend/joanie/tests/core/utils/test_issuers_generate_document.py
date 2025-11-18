"""Test suite for `generate_document` utility"""

import textwrap
from datetime import timedelta
from io import BytesIO

from django.template.exceptions import TemplateDoesNotExist
from django.test import TestCase

import markdown
from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import factories
from joanie.core.enums import (
    BATCH_ORDER_STATE_QUOTED,
    CONTRACT_DEFINITION_DEFAULT,
    CONTRACT_DEFINITION_UNICAMP,
    QUOTE_DEFAULT,
)
from joanie.core.utils import issuers
from joanie.core.utils.quotes import generate_document_context


class UtilsGenerateDocumentTestCase(TestCase):
    """Test suite for `generate_document` utility"""

    def create_contract_context(self, contract_title: str, fullname: str):
        """Create base context to generate contract .pdf file"""
        markdown_content = """
        ## Article 1
        The student must have a computer to follow the course

        ## Article 2
        The student and the organization are tied down to this contract

        ## Article 3
        The student has paid in advance the whole course before the start

        ## Terms and conditions
        Here are the terms and conditions of the current contract
        """
        body_content = markdown.markdown(textwrap.dedent(markdown_content))

        return {
            "contract": {
                "body": body_content,
                "title": contract_title,
                "description": "This is the contract definition",
            },
            "course": {
                "name": "Some course name",
            },
            "student": {
                "name": fullname,
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

    def test_utils_issuers_generate_document_raise_error_if_template_and_stylesheet_do_not_exist(
        self,
    ):
        """
        When the given name of the template .html and .css stylesheet do not exist,
        the method `generate_document` should raise the error `TemplateDoesNotExist`.
        """
        with self.assertRaises(TemplateDoesNotExist) as context:
            issuers.generate_document(name="convention", context=context)

        self.assertEqual(
            str(context.exception),
            "issuers/convention.html",
        )

    def test_utils_issuers_generate_document_contract_definition_default(self):
        """
        The method `generate_document` should create the .pdf document of the contract definition
        default when the given name of the .html and .css file exist. The passed context data
        should be available in the output of the file.
        """
        document_text = pdf_extract_text(
            BytesIO(
                issuers.generate_document(
                    name=CONTRACT_DEFINITION_DEFAULT,
                    context=self.create_contract_context(
                        contract_title="Contract Definition Default",
                        fullname="John Doe",
                    ),
                )
            )
        ).replace("\n", "")

        self.assertIn("Contract Definition Default", document_text)
        self.assertIn("John Doe", document_text)
        self.assertIn("1 Rue de L'Exemple, 75000 Paris (FR)", document_text)
        self.assertIn("must have a computer", document_text)
        self.assertIn("student and the organization are tied", document_text)
        self.assertIn("are the terms and conditions of the", document_text)
        self.assertIn("[SignatureField#1]", document_text)

    def test_utils_issuers_generate_document_contract_definition_unicamp(self):
        """
        The method `generate_document` should generate the contract definition unicamp
        when passing the `contract_definition_unicamp` because the .html template and
        .css stylesheet exist.
        """
        document_text = pdf_extract_text(
            BytesIO(
                issuers.generate_document(
                    name=CONTRACT_DEFINITION_UNICAMP,
                    context=self.create_contract_context(
                        contract_title="Contract Definition Unicamp",
                        fullname="Jane Doe",
                    ),
                )
            )
        ).replace("\n", "")

        self.assertIn("Contract Definition Unicamp", document_text)
        self.assertIn("Jane Doe", document_text)
        self.assertIn("1 Rue de L'Exemple, 75000 Paris (FR)", document_text)
        self.assertIn("must have a computer", document_text)
        self.assertIn("student and the organization are tied", document_text)
        self.assertIn("are the terms and conditions of the", document_text)
        self.assertIn("[SignatureField#1]", document_text)

    def test_utils_issuers_generate_document_quote_default(self):
        """
        The method `generate_document` should generate the quote when passing quote_default
        because the .html template and .css stylesheet exist.
        """
        organization = factories.OrganizationFactory(
            enterprise_code="SIRET_1234",
            activity_category_code="abcd1234",
        )
        batch_order = factories.BatchOrderFactory(
            organization=organization,
            offering__course=factories.CourseFactory(
                effort=timedelta(hours=11, minutes=00, seconds=00),
            ),
            nb_seats=2,
            state=BATCH_ORDER_STATE_QUOTED,
        )

        document_text = pdf_extract_text(
            BytesIO(
                issuers.generate_document(
                    name=QUOTE_DEFAULT,
                    context=generate_document_context(
                        quote_definition=batch_order.quote.definition,
                        batch_order=batch_order,
                    ),
                )
            )
        ).replace("\n", "")

        self.assertIn("Quote definition", document_text)
        self.assertIn("abcd1234", document_text)
        self.assertIn("SIRET_1234", document_text)
        self.assertIn("11 hours", document_text)
        self.assertIn("For number of seats: 2", document_text)
        # We should not find the tag for signing that is prepared for the signature provider
        self.assertNotIn("[SignatureField#1]", document_text)
