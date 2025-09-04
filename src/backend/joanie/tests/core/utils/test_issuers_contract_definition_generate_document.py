"""Test suite for utility method to generate document of Contract Definition in PDF bytes format"""

from datetime import datetime, timedelta
from io import BytesIO

from django.contrib.sites.models import Site
from django.test import TestCase

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories
from joanie.core.models import CourseState
from joanie.core.utils import contract_definition as contract_definition_utility
from joanie.core.utils import issuers
from joanie.payment.factories import InvoiceFactory


def format_datetime(datetime_value):
    """
    Format a datetime value to a string with a specific format, including minutes if present.
    """
    string_format = f"%m/%d/%Y %-I{':%M' if datetime_value.minute else ''} %p"

    return (
        datetime_value.strftime(string_format)
        .lower()
        .replace("am", "a.m.")
        .replace("pm", "p.m.")
    )


class UtilsIssuersContractDefinitionGenerateDocument(TestCase):
    """
    Test suite for issuer utility method to generate document of contract definition in PDF bytes
    format.
    """

    def test_format_datetime(self):
        """
        Test the format_datetime utility function.
        """
        self.assertEqual(
            format_datetime(datetime(2022, 1, 1, 12, 30)), "01/01/2022 12:30 p.m."
        )
        self.assertEqual(
            format_datetime(datetime(2022, 1, 1, 12, 0)), "01/01/2022 12 p.m."
        )

    # ruff : noqa : PLR0915
    # pylint: disable=too-many-statements
    def test_utils_issuers_contract_definition_generate_document(self):
        """
        Issuer 'generate document' method should generate a contract definition document.
        """
        user = factories.UserFactory(
            email="student@example.fr",
            first_name="Rooky",
            last_name="The Student",
            phone_number="0612345678",
        )

        definition = factories.ContractDefinitionFactory(
            title="Contract Definition Title",
            description="Contract Definition Description",
            body="""
            ## Contract Definition Body
            Lorem ipsum sit body est
            """,
            appendix="""
            ### Terms and conditions
            Terms and Conditions Content
            """,
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
        run = factories.CourseRunFactory(state=CourseState.ONGOING_OPEN)
        product = factories.ProductFactory(
            title="You will know that you know you don't know",
            price="999.99",
            contract_definition_order=definition,
            target_courses=[run.course],
        )

        course = factories.CourseFactory(code="UX-00001", effort=timedelta(hours=404))

        offering = factories.OfferingFactory(
            product=product, course=course, organizations=[organization]
        )

        order = factories.OrderFactory(
            owner=user,
            product=offering.product,
            course=offering.course,
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
        order.generate_schedule()

        file_bytes = issuers.generate_document(
            name=order.contract.definition.name,
            context=order.contract.context,
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
        self.assertIn(format_datetime(run.start), document_text, document_text)
        self.assertIn(format_datetime(run.end), document_text, document_text)
        self.assertIn("404 hours", document_text)
        self.assertIn("999.99 €", document_text)

        # - Contract content should be displayed
        self.assertIn("Contract Definition Body", document_text)
        self.assertIn("Lorem ipsum sit body est", document_text)

        # - Appendices title should be displayed
        self.assertIn("Appendices", document_text)
        self.assertIn("Terms and conditions", document_text)
        self.assertIn("Terms and Conditions Content", document_text)
        # - Payment schedule should be displayed
        self.assertIn("Payment schedule", document_text)
        self.assertIn("Due date", document_text)
        self.assertIn("Amount", document_text)
        for installment in order.payment_schedule:
            self.assertIn(installment["due_date"].strftime("%m/%d/%Y"), document_text)
            self.assertIn(f"{installment['amount']:.2f}\xa0€", document_text)
        self.assertIn("Total :  999.99\xa0€", document_text)
        # - Syllabus should not be displayed
        self.assertNotIn("Syllabus", document_text)

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
            body="""
            ## Contract Definition Body,
            ## Terms and conditions
            Terms and Conditions Content
            """,
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
        self.assertIn("Terms and conditions", document_text)
        self.assertIn("Terms and Conditions Content", document_text)

        # - Appendices should not be displayed
        self.assertNotIn("Appendices", document_text)
        self.assertNotIn("Payment schedule", document_text)
        self.assertNotIn("Syllabus", document_text)

        # - Signature slots should be displayed
        self.assertIn("Learner's signature", document_text)
        self.assertIn("[SignatureField#1]", document_text)
        self.assertIn("University representative's signature", document_text)
        self.assertIn("[SignatureField#2]", document_text)
