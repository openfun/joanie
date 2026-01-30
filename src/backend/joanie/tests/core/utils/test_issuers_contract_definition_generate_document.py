"""Test suite for utility method to generate document of Contract Definition in PDF bytes format"""

from datetime import timedelta
from io import BytesIO

from django.contrib.sites.models import Site
from django.test import TestCase

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories
from joanie.core.models import CourseState
from joanie.core.utils import contract_definition as contract_definition_utility
from joanie.core.utils import issuers
from joanie.core.utils.contract_definition import format_course_date
from joanie.payment.factories import InvoiceFactory


class UtilsIssuersContractDefinitionGenerateDocument(TestCase):
    """
    Test suite for issuer utility method to generate document of contract definition in PDF bytes
    format.
    """

    # ruff : noqa : PLR0915
    # pylint: disable=too-many-statements, too-many-locals
    def test_utils_issuers_contract_definition_generate_document(self):
        """
        Issuer 'generate document' method should generate a contract definition document.
        """
        # Prepare User and Organization Data
        user = factories.UserFactory(
            email="student@example.fr",
            first_name="Rooky",
            last_name="The Student",
            phone_number="0612345678",
        )
        user_address = factories.UserAddressFactory(
            owner=user,
            first_name="Rocky",
            last_name="The Student",
            address="1 Rue de l'Apprenant",
            postcode="58000",
            city="Nevers",
            country="FR",
            title="Office",
            is_main=False,
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
        # Prepare the order
        language_code = "fr-fr"
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
            name=enums.CONTRACT_DEFINITION_DEFAULT,
            language=language_code,
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
        order = factories.OrderGeneratorFactory(
            owner=user,
            product=offering.product,
            course=offering.course,
            organization=organization,
            state=enums.ORDER_STATE_SIGNING,
            main_invoice=InvoiceFactory(recipient_address=user_address),
        )
        # Prepare start and end course dates
        course_dates = order.get_equivalent_course_run_dates()

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
        self.assertIn(
            format_course_date(course_dates["start"], language_code), document_text
        )
        self.assertIn(
            format_course_date(course_dates["end"], language_code), document_text
        )
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
            name=enums.CONTRACT_DEFINITION_UNICAMP,
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

    def test_utils_issuers_contract_definition_generate_document_for_batch_order(self):
        """
        Issuer `generate_document` should generate the contract for the batch order.
        """
        organization = factories.OrganizationFactory(
            title="University X",
            dpo_email="dpojohnnydoes@example.fr",
            contact_email="contact@example.fr",
            contact_phone="0123456789",
            enterprise_code="ENTRCODE1234",
            activity_category_code="ACTCATCODE1234",
            representative="John Doe",
            representative_profession="Educational representative",
            signatory_representative="Big boss",
            signatory_representative_profession="Director",
        )
        factories.OrganizationAddressFactory(
            organization=organization,
            owner=None,
            address="1 Rue de l'Université",
            postcode="75000",
            city="Paris",
            country="FR",
            is_reusable=True,
            is_main=True,
        )
        run = factories.CourseRunFactory(state=CourseState.ONGOING_OPEN)
        language_code = "en-us"
        product = factories.ProductFactory(
            title="You know nothing Jon Snow",
            target_courses=[run.course],
            quote_definition=factories.QuoteDefinitionFactory(),
            contract_definition_batch_order=factories.ContractDefinitionFactory(
                name=enums.PROFESSIONAL_TRAINING_AGREEMENT_UNICAMP,
                title="Professional Training Agreement",
                description="Professional Training Agreement description",
                body="Article of the professional training agreement",
                appendix="Appendices",
                language=language_code,
            ),
        )
        course = factories.CourseFactory(code="00002", effort=timedelta(hours=404))
        offering = factories.OfferingFactory(
            product=product, course=course, organizations=[organization]
        )
        batch_order = factories.BatchOrderFactory(
            organization=organization,
            offering=offering,
            nb_seats=2,
            state=enums.BATCH_ORDER_STATE_TO_SIGN,
            vat_registration="VAT_NUMBER_123",
            company_name="Acme Org",
            address="Street of awesomeness",
            postcode="00000",
            city="Unknown City",
            country="FR",
            administrative_firstname="Jon",
            administrative_lastname="Snow",
            administrative_profession="Buyer",
            administrative_email="jonsnow@example.acme",
            administrative_telephone="0123457890",
            signatory_firstname="Janette",
            signatory_lastname="Doe",
            signatory_email="janette@example.acme",
            signatory_telephone="0987654321",
            signatory_profession="Manager",
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )
        course_dates = batch_order.get_equivalent_course_run_dates()

        file_bytes = issuers.generate_document(
            name=batch_order.contract.definition.name,
            context=batch_order.contract.context,
        )

        document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", " ")

        self.assertIn("Professional Training Agreement", document_text)
        self.assertIn("Professional Training Agreement description", document_text)
        self.assertIn(
            "The current contract is formed between "
            "the University and the Company, as identified below:",
            document_text,
        )

        # - Organization information should be displayed
        self.assertIn("University X", document_text)
        self.assertIn("1 Rue de l'Université, 75000 Paris (FR)", document_text)
        self.assertIn("ENTRCODE1234", document_text)
        self.assertIn("ACTCATCODE1234", document_text)
        self.assertIn("John Doe - Educational representative", document_text)
        self.assertIn("Big boss - Director", document_text)
        self.assertIn("contact@example.fr - 0123456789", document_text)
        self.assertIn("dpojohnnydoes@example.fr", document_text)

        # - Batch order Company's information should be displayed
        self.assertIn("Acme Org", document_text)
        self.assertIn("Street of awesomeness", document_text)
        self.assertIn("00000", document_text)
        self.assertIn("Unknown City", document_text)
        self.assertIn("FR", document_text)
        # Administrative representative part
        self.assertIn("Jon Snow - Buyer", document_text)
        self.assertIn("jonsnow@example.acme", document_text)
        self.assertIn("0123457890", document_text)
        # Signatory part
        self.assertIn("Janette Doe", document_text)
        self.assertIn("Manager", document_text)

        # - Course information should be displayed
        self.assertIn("00002", document_text)
        self.assertIn("You know nothing Jon Snow", document_text)
        self.assertIn(
            format_course_date(course_dates["start"], language_code), document_text
        )
        self.assertIn(
            format_course_date(course_dates["end"], language_code), document_text
        )
        self.assertIn("404 hours", document_text)
        self.assertIn("100.00 €", document_text)
        self.assertIn("50.00 €", document_text)

        # - Appendices should be displayed
        self.assertIn("Appendices", document_text)
        # - Payment schedule should not be displayed
        self.assertNotIn("Payment schedule", document_text)
        # - Syllabus should not be displayed
        self.assertNotIn("Syllabus", document_text)

        # - Signature slots should be displayed
        self.assertIn("Company's signatory signature", document_text)
        self.assertIn("[SignatureField#1]", document_text)
        self.assertIn("University representative's signature", document_text)
        self.assertIn("[SignatureField#2]", document_text)
