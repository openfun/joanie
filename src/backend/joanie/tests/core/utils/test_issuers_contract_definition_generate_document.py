"""Test suite for utility method to generate document of Contract Definition in PDF bytes format"""

from datetime import timedelta
from io import BytesIO

from django.contrib.sites.models import Site
from django.test import TestCase

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories
from joanie.core.utils import contract_definition as contract_definition_utility
from joanie.core.utils import issuers
from joanie.payment.factories import InvoiceFactory


class UtilsIssuersContractDefinitionGenerateDocument(TestCase):
    """
    Test suite for issuer utility method to generate document of contract definition in PDF bytes
    format.
    """

    def test_utils_issuers_contract_definition_generate_document(self):
        """
        Issuer 'generate document' method should generate a contract definition document.
        """
        factories.SiteConfigFactory(
            site=Site.objects.get_current(),
            terms_and_conditions="Terms and Conditions Content",
        )

        user = factories.UserFactory(
            email="student@example.fr",
            first_name="Rooky",
            last_name="The Student",
            phone_number="0612345678",
        )

        definition = factories.ContractDefinitionFactory(
            title="Contract Definition Title",
            description="Contract Definition Description",
            body="## Contract Definition Body",
        )

        organization = factories.OrganizationFactory(
            title="University X",
            activity_category_code="8542Z",
            enterprise_code="UX-74392-899",
            representative="John Doe",
            representative_profession="Director",
            signatory_representative="Jane Doe",
            signatory_representative_profession="Administrative Manager",
            contact_phone="+33712345678",
            contact_email="contact@university-x.xyz",
            dpo_email="dpo@university-x.xyz",
        )

        factories.OrganizationAddressFactory(
            organization=organization,
            owner=None,
            address="1 Rue de l'Université",
            postcode="87000",
            city="Limoges",
            country="FR",
            is_reusable=True,
            is_main=True,
        )

        product = factories.ProductFactory(
            title="You will know that you know you don't know",
            price="999.99",
            contract_definition=definition,
            target_courses=[
                factories.CourseFactory(
                    course_runs=[
                        factories.CourseRunFactory(
                            start="2024-01-01T09:00:00+00:00",
                            end="2024-03-31T18:00:00+00:00",
                            enrollment_start="2024-01-01T12:00:00+00:00",
                            enrollment_end="2024-02-01T12:00:00+00:00",
                        )
                    ]
                )
            ],
        )

        course = factories.CourseFactory(code="UX-00001", effort=timedelta(hours=404))

        relation = factories.CourseProductRelationFactory(
            product=product, course=course, organizations=[organization]
        )

        order = factories.OrderFactory(
            owner=user,
            product=relation.product,
            course=relation.course,
            organization=organization,
            state=enums.ORDER_STATE_COMPLETED,
            main_invoice=InvoiceFactory(
                recipient_address=factories.UserAddressFactory(
                    owner=user,
                    address="1 Rue de l'Apprenant",
                    postcode="58000",
                    city="Nevers",
                    country="FR",
                )
            ),
        )
        contract = factories.ContractFactory(
            order=order,
            context=contract_definition_utility.generate_document_context(
                contract_definition=definition, user=user, order=order
            ),
            definition_checksum="1234",
        )
        contract.refresh_from_db()

        file_bytes = issuers.generate_document(
            name=contract.definition.name,
            context=contract.context,
        )
        document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", " ")

        self.assertIn("Contract Definition Title", document_text)
        self.assertIn("Contract Definition Description", document_text)
        self.assertIn(
            "The current contract is formed between "
            "the University and the Learner, as identified below:",
            document_text,
        )

        # - Organization information should be displayed
        self.assertIn("University X", document_text)
        self.assertIn("1 Rue de l'Université, 87000 Limoges (FR)", document_text)
        self.assertIn("UX-74392-899", document_text)
        self.assertIn("8542Z", document_text)
        self.assertIn("John Doe - Director", document_text)
        self.assertIn("Jane Doe - Administrative Manager", document_text)
        self.assertIn("contact@university-x.xyz - +33712345678", document_text)
        self.assertIn("dpo@university-x.xyz", document_text)

        # - Student information should be displayed
        self.assertIn("Rooky The Student", document_text)
        self.assertIn("1 Rue de l'Apprenant, 58000 Nevers (FR)", document_text)
        self.assertIn("student@example.fr", document_text)
        self.assertIn("0612345678", document_text)

        # - Course information should be displayed
        self.assertIn("UX-00001", document_text)
        self.assertIn("You will know that you know you don't know", document_text)
        self.assertIn("01/01/2024 9 a.m.", document_text)
        self.assertIn("03/31/2024 6 p.m.", document_text)
        self.assertIn("404 hours", document_text)
        self.assertIn("999.99 €", document_text)

        # - Contract content should be displayed
        self.assertIn("Contract Definition Body", document_text)

        # - Appendices should be displayed
        self.assertIn("Appendices", document_text)
        self.assertIn("Terms and conditions", document_text)
        self.assertIn("Terms and Conditions Content", document_text)

        # - Signature slots should be displayed
        self.assertIn("Learner's signature", document_text)
        self.assertIn("[SignatureField#1]", document_text)
        self.assertIn("University representative's signature", document_text)
        self.assertIn("[SignatureField#2]", document_text)

    def test_utils_issuers_contract_definition_generate_document_with_placeholders(
        self,
    ):
        """
        Issuer 'generate document' method should generate a contract definition document
        with placeholders
        """
        factories.SiteConfigFactory(
            site=Site.objects.get_current(),
            terms_and_conditions="Terms and Conditions Content",
        )

        definition = factories.ContractDefinitionFactory(
            title="Contract Definition Title",
            description="Contract Definition Description",
            body="## Contract Definition Body",
        )

        context = contract_definition_utility.generate_document_context(
            contract_definition=definition
        )

        file_bytes = issuers.generate_document(
            name=definition.name,
            context=context,
        )
        document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", " ")

        self.assertIn("Contract Definition Title", document_text)
        self.assertIn("Contract Definition Description", document_text)
        self.assertIn(
            "The current contract is formed between "
            "the University and the Learner, as identified below:",
            document_text,
        )

        # - Organization information should be displayed
        self.assertIn("<ORGANIZATION_NAME>", document_text)
        self.assertIn(
            "<ORGANIZATION_ADDRESS_STREET_NAME>, "
            "<ORGANIZATION_ADDRESS_POSTCODE> <ORGANIZATION_ADDRESS_CITY> "
            "(<ORGANIZATION_ADDRESS_COUNTRY>)",
            document_text,
        )
        self.assertIn("<ENTERPRISE_CODE>", document_text)
        self.assertIn("<ACTIVITY_CATEGORY_CODE>", document_text)
        self.assertIn("<REPRESENTATIVE> - <REPRESENTATIVE_PROFESSION>", document_text)
        self.assertIn(
            "<SIGNATORY_REPRESENTATIVE> - <SIGNATURE_REPRESENTATIVE_PROFESSION>",
            document_text,
        )
        self.assertIn("<CONTACT_EMAIL> - <CONTACT_PHONE>", document_text)
        self.assertIn("<DPO_EMAIL_ADDRESS>", document_text)

        # - Student information should be displayed
        self.assertIn("<STUDENT_NAME>", document_text)
        self.assertIn(
            "<STUDENT_ADDRESS_STREET_NAME>, "
            "<STUDENT_ADDRESS_POSTCODE> <STUDENT_ADDRESS_CITY> "
            "(<STUDENT_ADDRESS_COUNTRY>)",
            document_text,
        )
        self.assertIn("<STUDENT_EMAIL>", document_text)
        self.assertIn("<STUDENT_PHONE_NUMBER>", document_text)

        # - Course information should be displayed
        self.assertIn("<COURSE_CODE>", document_text)
        self.assertIn("<COURSE_NAME>", document_text)
        self.assertIn("<COURSE_START_DATE>", document_text)
        self.assertIn("<COURSE_END_DATE>", document_text)
        self.assertIn("<COURSE_EFFORT>", document_text)
        self.assertIn("<COURSE_PRICE>", document_text)

        # - Contract content should be displayed
        self.assertIn("Contract Definition Body", document_text)

        # - Appendices should be displayed
        self.assertIn("Appendices", document_text)
        self.assertIn("Terms and conditions", document_text)
        self.assertIn("Terms and Conditions Content", document_text)

        # - Signature slots should be displayed
        self.assertIn("Learner's signature", document_text)
        self.assertIn("[SignatureField#1]", document_text)
        self.assertIn("University representative's signature", document_text)
        self.assertIn("[SignatureField#2]", document_text)
