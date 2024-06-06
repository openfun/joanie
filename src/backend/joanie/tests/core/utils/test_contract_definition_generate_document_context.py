"""Test suite for `generate_document_context` utility"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from unittest import mock

from django.contrib.sites.models import Site
from django.test import TestCase, override_settings
from django.utils import timezone as django_timezone

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories
from joanie.core.utils import contract_definition, image_to_base64, issuers
from joanie.payment.factories import InvoiceFactory


def _processor_for_test_suite(context):
    """A processor for the test of the document context generation."""
    course_code = context["course"]["code"]
    contract_language = context["contract"]["language"]

    return {
        "extra": {
            "course_code": course_code,
            "language_code": contract_language,
            "is_for_test": True,
        }
    }


class UtilsGenerateDocumentContextTestCase(TestCase):
    """Test suite for `generate_document_context` utility"""

    maxDiff = None

    def test_utils_contract_definition_generate_document_context_with_order(self):
        """
        When we generate the document context for a contract definition with an order,
        it should return a context with all the data attached to the contract definition,
        the user, the order and the terms and conditions of the current site.
        """
        user = factories.UserFactory(
            email="johndoe@example.fr",
            first_name="John Doe",
            last_name="",
            phone_number="0123456789",
        )
        factories.SiteConfigFactory(
            site=Site.objects.get_current(),
            terms_and_conditions="## Terms and conditions",
        )
        user_address = factories.UserAddressFactory(
            owner=user,
            first_name="John",
            last_name="Doe",
            address="5 Rue de L'Exemple",
            postcode="75000",
            city="Paris",
            country="FR",
            title="Office",
            is_main=False,
        )
        organization = factories.OrganizationFactory(
            dpo_email="johnnydoes@example.fr",
            contact_email="contact@example.fr",
            contact_phone="0123456789",
            enterprise_code="1234",
            activity_category_code="abcd1234",
            representative="Mister Example",
            representative_profession="Educational representative",
            signatory_representative="Big boss",
            signatory_representative_profession="Director",
        )
        address_organization = factories.OrganizationAddressFactory(
            organization=organization,
            owner=None,
            is_main=True,
            is_reusable=True,
        )
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product=factories.ProductFactory(
                contract_definition=factories.ContractDefinitionFactory(
                    title="CONTRACT DEFINITION 1",
                    description="Contract definition description",
                    body="Articles de la convention",
                    language="en-us",
                ),
                title="You will know that you know you don't know",
                price="999.99",
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
            ),
            course=factories.CourseFactory(
                organizations=[organization],
                effort=timedelta(hours=10, minutes=30, seconds=12),
            ),
        )
        order = factories.OrderFactory(
            owner=user,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_VALIDATED,
            main_invoice=InvoiceFactory(recipient_address=user_address),
        )
        factories.OrderTargetCourseRelationFactory(
            course=relation.course, order=order, position=1
        )
        expected_context = {
            "contract": {
                "body": "<p>Articles de la convention</p>",
                "description": "Contract definition description",
                "title": "CONTRACT DEFINITION 1",
                "language": "en-us",
            },
            "course": {
                "name": order.product.title,
                "code": relation.course.code,
                "start": "2024-01-01T09:00:00+00:00",
                "end": "2024-03-31T18:00:00+00:00",
                "effort": "P0DT10H30M12S",
                "price": "999.99",
                "currency": "€",
            },
            "student": {
                "name": user.get_full_name(),
                "address": {
                    "id": str(user_address.id),
                    "address": user_address.address,
                    "city": user_address.city,
                    "country": str(user_address.country),
                    "last_name": user_address.last_name,
                    "first_name": user_address.first_name,
                    "postcode": user_address.postcode,
                    "title": user_address.title,
                    "is_main": user_address.is_main,
                },
                "email": user.email,
                "phone_number": str(user.phone_number),
            },
            "organization": {
                "address": {
                    "id": str(address_organization.id),
                    "address": address_organization.address,
                    "city": address_organization.city,
                    "country": str(address_organization.country),
                    "last_name": address_organization.last_name,
                    "first_name": address_organization.first_name,
                    "postcode": address_organization.postcode,
                    "title": address_organization.title,
                    "is_main": address_organization.is_main,
                },
                "logo": image_to_base64(order.organization.logo),
                "name": organization.title,
                "representative": organization.representative,
                "representative_profession": organization.representative_profession,
                "enterprise_code": organization.enterprise_code,
                "activity_category_code": organization.activity_category_code,
                "signatory_representative": organization.signatory_representative,
                "signatory_representative_profession": (
                    organization.signatory_representative_profession
                ),
                "contact_phone": organization.contact_phone,
                "contact_email": organization.contact_email,
                "dpo_email": organization.dpo_email,
            },
        }

        context = contract_definition.generate_document_context(
            contract_definition=order.product.contract_definition,
            user=user,
            order=order,
        )

        self.assertEqual(context, expected_context)

    def test_utils_contract_definition_generate_document_context_without_order(self):
        """
        When we generate the document context for a contract definition without an order and
        the user's address, it should return default values for the keys :
        `student.address`,
        `course.start`, `course.end`, `course.effort`, `course.price`
        `course.name`, `organization.logo`, `organization.signature`, `organization.title`.
        `organization.address`, `organization.representative`, `organization.enterprise_code`,
        `organization.activity_category_code` `organization.signatory_representative`,
        `organization.contact_phone`, `organization.signatory_representative_profession`,
        `organization.contact_email` `organization.dpo_email`,
        `organization.representative_profession`.
        """
        organization_fallback_logo = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
            "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
        )
        user = factories.UserFactory(
            email="student@example.fr",
            first_name="John Doe",
            last_name="",
            phone_number="0123456789",
        )
        definition = factories.ContractDefinitionFactory(
            title="CONTRACT DEFINITION 2",
            body="Articles de la convention",
            description="Contract definition description",
            language="fr-fr",
        )
        expected_context = {
            "contract": {
                "body": "<p>Articles de la convention</p>",
                "description": "Contract definition description",
                "title": "CONTRACT DEFINITION 2",
                "language": "fr-fr",
            },
            "course": {
                "name": "<COURSE_NAME>",
                "code": "<COURSE_CODE>",
                "start": "<COURSE_START_DATE>",
                "end": "<COURSE_END_DATE>",
                "effort": "<COURSE_EFFORT>",
                "price": "<COURSE_PRICE>",
                "currency": "€",
            },
            "student": {
                "name": user.get_full_name(),
                "address": {
                    "address": "<STUDENT_ADDRESS_STREET_NAME>",
                    "city": "<STUDENT_ADDRESS_CITY>",
                    "country": "<STUDENT_ADDRESS_COUNTRY>",
                    "last_name": "<STUDENT_LAST_NAME>",
                    "first_name": "<STUDENT_FIRST_NAME>",
                    "postcode": "<STUDENT_ADDRESS_POSTCODE>",
                    "title": "<STUDENT_ADDRESS_TITLE>",
                    "is_main": True,
                },
                "email": str(user.email),
                "phone_number": str(user.phone_number),
            },
            "organization": {
                "address": {
                    "address": "<ORGANIZATION_ADDRESS_STREET_NAME>",
                    "city": "<ORGANIZATION_ADDRESS_CITY>",
                    "country": "<ORGANIZATION_ADDRESS_COUNTRY>",
                    "last_name": "<ORGANIZATION_LAST_NAME>",
                    "first_name": "<ORGANIZATION_FIRST_NAME>",
                    "postcode": "<ORGANIZATION_ADDRESS_POSTCODE>",
                    "title": "<ORGANIZATION_ADDRESS_TITLE>",
                    "is_main": True,
                },
                "logo": organization_fallback_logo,
                "name": "<ORGANIZATION_NAME>",
                "representative": "<REPRESENTATIVE>",
                "representative_profession": "<REPRESENTATIVE_PROFESSION>",
                "enterprise_code": "<ENTERPRISE_CODE>",
                "activity_category_code": "<ACTIVITY_CATEGORY_CODE>",
                "signatory_representative": "<SIGNATORY_REPRESENTATIVE>",
                "signatory_representative_profession": "<SIGNATURE_REPRESENTATIVE_PROFESSION>",
                "contact_phone": "<CONTACT_PHONE>",
                "contact_email": "<CONTACT_EMAIL>",
                "dpo_email": "<DPO_EMAIL_ADDRESS>",
            },
        }

        context = contract_definition.generate_document_context(
            contract_definition=definition, user=user
        )

        self.assertDictEqual(context, expected_context)

    def test_utils_contract_definition_generate_document_context_default_placeholders_values(
        self,
    ):
        """
        When we generate the document context for the contract definition without : an order
        and a user, it should return the default placeholder values for different sections
        of the context.
        """
        organization_fallback_logo = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
            "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
        )
        definition = factories.ContractDefinitionFactory(
            title="CONTRACT DEFINITION 3",
            description="Contract definition description",
            body="Articles de la convention",
            language="fr-fr",
        )
        expected_context = {
            "contract": {
                "body": "<p>Articles de la convention</p>",
                "description": "Contract definition description",
                "title": "CONTRACT DEFINITION 3",
                "language": "fr-fr",
            },
            "course": {
                "name": "<COURSE_NAME>",
                "code": "<COURSE_CODE>",
                "start": "<COURSE_START_DATE>",
                "end": "<COURSE_END_DATE>",
                "effort": "<COURSE_EFFORT>",
                "price": "<COURSE_PRICE>",
                "currency": "€",
            },
            "student": {
                "name": "<STUDENT_NAME>",
                "address": {
                    "address": "<STUDENT_ADDRESS_STREET_NAME>",
                    "city": "<STUDENT_ADDRESS_CITY>",
                    "country": "<STUDENT_ADDRESS_COUNTRY>",
                    "last_name": "<STUDENT_LAST_NAME>",
                    "first_name": "<STUDENT_FIRST_NAME>",
                    "postcode": "<STUDENT_ADDRESS_POSTCODE>",
                    "title": "<STUDENT_ADDRESS_TITLE>",
                    "is_main": True,
                },
                "email": "<STUDENT_EMAIL>",
                "phone_number": "<STUDENT_PHONE_NUMBER>",
            },
            "organization": {
                "address": {
                    "address": "<ORGANIZATION_ADDRESS_STREET_NAME>",
                    "city": "<ORGANIZATION_ADDRESS_CITY>",
                    "country": "<ORGANIZATION_ADDRESS_COUNTRY>",
                    "last_name": "<ORGANIZATION_LAST_NAME>",
                    "first_name": "<ORGANIZATION_FIRST_NAME>",
                    "postcode": "<ORGANIZATION_ADDRESS_POSTCODE>",
                    "title": "<ORGANIZATION_ADDRESS_TITLE>",
                    "is_main": True,
                },
                "logo": organization_fallback_logo,
                "name": "<ORGANIZATION_NAME>",
                "representative": "<REPRESENTATIVE>",
                "representative_profession": "<REPRESENTATIVE_PROFESSION>",
                "enterprise_code": "<ENTERPRISE_CODE>",
                "activity_category_code": "<ACTIVITY_CATEGORY_CODE>",
                "signatory_representative": "<SIGNATORY_REPRESENTATIVE>",
                "signatory_representative_profession": "<SIGNATURE_REPRESENTATIVE_PROFESSION>",
                "contact_phone": "<CONTACT_PHONE>",
                "contact_email": "<CONTACT_EMAIL>",
                "dpo_email": "<DPO_EMAIL_ADDRESS>",
            },
        }

        context = contract_definition.generate_document_context(
            contract_definition=definition
        )

        self.assertDictEqual(context, expected_context)

    @override_settings(
        JOANIE_DOCUMENT_ISSUER_CONTEXT_PROCESSORS={
            "contract_definition": [
                "joanie.tests.core.utils.test_contract_definition_generate_document_context._processor_for_test_suite"  # pylint: disable=line-too-long
            ]
        }
    )
    @mock.patch(
        "joanie.tests.core.utils.test_contract_definition_generate_document_context._processor_for_test_suite",  # pylint: disable=line-too-long
        side_effect=_processor_for_test_suite,
    )
    def test_utils_contract_definition_generate_document_context_processors(
        self, _mock_processor_for_test
    ):
        """
        If contract definition context processors are defined through settings, those should be
        called and their results should be merged into the final context.
        """
        definition = factories.ContractDefinitionFactory(
            title="CONTRACT DEFINITION 3",
            description="Contract definition description",
            body="Articles de la convention",
            language="fr-fr",
        )

        context = contract_definition.generate_document_context(
            contract_definition=definition
        )
        _mock_processor_for_test.assert_called_once_with(context)
        self.assertEqual(
            context["extra"],
            {
                "course_code": "<COURSE_CODE>",
                "language_code": "fr-fr",
                "is_for_test": True,
            },
        )

    @override_settings(
        JOANIE_DOCUMENT_ISSUER_CONTEXT_PROCESSORS={
            "contract_definition": [
                "joanie.tests.core.test_utils_contract_definition_generate_document_context.unknown_processor"  # pylint: disable=line-too-long
            ]
        }
    )
    def test_utils_contract_definition_generate_document_context_processor_mis_configured(
        self,
    ):
        """
        If contract definition context processors
        are misconfigured, an ImportError should be raised.
        """
        definition = factories.ContractDefinitionFactory(
            title="CONTRACT DEFINITION 3",
            description="Contract definition description",
            body="Articles de la convention",
            language="fr-fr",
        )

        with self.assertRaises(ImportError):
            contract_definition.generate_document_context(
                contract_definition=definition
            )

    def test_utils_contract_definition_generate_document_context_course_data_section_checks(
        self,
    ):
        """
        When we call `generate_document_context` utility method, we need to verify the type
        of each values in the section course (course start, course end, effort and price) need
        to be saved as 'string' in the context.
        """
        user = factories.UserFactory(
            email="johndoe@example.fr",
            first_name="John Doe",
            last_name="",
            phone_number="0123456789",
        )
        factories.SiteConfigFactory(
            site=Site.objects.get_current(),
            terms_and_conditions="## Terms and conditions",
        )
        user_address = factories.UserAddressFactory(
            owner=user,
            first_name="John",
            last_name="Doe",
            address="5 Rue de L'Exemple",
            postcode="75000",
            city="Paris",
            country="FR",
            title="Office",
            is_main=False,
        )
        organization = factories.OrganizationFactory(
            dpo_email="johnnydoes@example.fr",
            contact_email="contact@example.fr",
            contact_phone="0123456789",
            enterprise_code="1234",
            activity_category_code="abcd1234",
            representative="Mister Example",
            representative_profession="Educational representative",
            signatory_representative="Big boss",
            signatory_representative_profession="Director",
        )
        factories.OrganizationAddressFactory(
            organization=organization,
            owner=None,
            is_main=True,
            is_reusable=True,
        )
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product=factories.ProductFactory(
                contract_definition=factories.ContractDefinitionFactory(
                    title="CONTRACT DEFINITION 1",
                    description="Contract definition description",
                    body="Articles de la convention",
                    language="en-us",
                ),
                title="You will know that you know you don't know",
                price="999.99",
                target_courses=[
                    factories.CourseFactory(
                        course_runs=[
                            factories.CourseRunFactory(
                                start="2024-02-01T10:00:00+00:00",
                                end="2024-05-31T20:00:00+00:00",
                                enrollment_start="2024-02-01T12:00:00+00:00",
                                enrollment_end="2024-02-01T12:00:00+00:00",
                            )
                        ]
                    )
                ],
            ),
            course=factories.CourseFactory(
                organizations=[organization],
                effort=timedelta(hours=22, minutes=45, seconds=20),
            ),
        )

        order = factories.OrderFactory(
            owner=user,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_VALIDATED,
            main_invoice=InvoiceFactory(recipient_address=user_address),
        )
        factories.OrderTargetCourseRelationFactory(
            course=relation.course, order=order, position=1
        )
        course_dates = order.get_equivalent_course_run_dates()

        context = contract_definition.generate_document_context(
            contract_definition=order.product.contract_definition,
            user=user,
            order=order,
        )
        contract = factories.ContractFactory(
            order=order,
            signature_backend_reference="abcd",
            context=context,
            student_signed_on=django_timezone.now(),
            organization_signed_on=django_timezone.now(),
        )

        # Course effort check
        self.assertIsInstance(order.course.effort, timedelta)
        self.assertIsInstance(context["course"]["effort"], str)
        self.assertIsInstance(contract.context["course"]["effort"], str)
        self.assertEqual(
            order.course.effort, timedelta(hours=22, minutes=45, seconds=20)
        )
        self.assertEqual(contract.context["course"]["effort"], "P0DT22H45M20S")
        # Course start check
        self.assertIsInstance(course_dates["start"], datetime)
        self.assertIsInstance(context["course"]["start"], str)
        self.assertIsInstance(contract.context["course"]["start"], str)
        self.assertEqual(
            course_dates["start"], datetime(2024, 2, 1, 10, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(
            contract.context["course"]["start"], "2024-02-01T10:00:00+00:00"
        )
        # Course end check
        self.assertIsInstance(course_dates["end"], datetime)
        self.assertIsInstance(context["course"]["end"], str)
        self.assertIsInstance(contract.context["course"]["end"], str)
        self.assertEqual(
            course_dates["end"], datetime(2024, 5, 31, 20, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(contract.context["course"]["end"], "2024-05-31T20:00:00+00:00")
        # Pricing check
        self.assertIsInstance(order.total, Decimal)
        self.assertIsInstance(context["course"]["price"], str)
        self.assertIsInstance(contract.context["course"]["price"], str)
        self.assertEqual(order.total, Decimal("999.99"))
        self.assertEqual(contract.context["course"]["price"], "999.99")

    @override_settings(
        JOANIE_DOCUMENT_ISSUER_CONTEXT_PROCESSORS={
            "contract_definition": [
                "joanie.tests.core.utils.test_contract_definition_generate_document_context._processor_for_test_suite"  # pylint: disable=line-too-long
            ]
        }
    )
    @mock.patch(
        "joanie.tests.core.utils.test_contract_definition_generate_document_context._processor_for_test_suite",  # pylint: disable=line-too-long
        side_effect=_processor_for_test_suite,
    )
    def test_utils_contract_definition_generate_document_context_processors_with_syllabus(
        self, mock_processor_for_test
    ):
        """
        If contract definition context processors are defined through settings, those should be
        called and their results should be merged into the final context. We should find the terms
        and conditions within the body of the contract and the `appendices` section with the
        syllabus context in the document.
        """
        user = factories.UserFactory(
            email="johndoe@example.fr",
            first_name="John Doe",
            last_name="",
            phone_number="0123456789",
        )
        user_address = factories.UserAddressFactory(
            owner=user,
            first_name="John",
            last_name="Doe",
            address="5 Rue de L'Exemple",
            postcode="75000",
            city="Paris",
            country="FR",
            title="Office",
            is_main=False,
        )
        organization = factories.OrganizationFactory(
            dpo_email="johnnydoes@example.fr",
            contact_email="contact@example.fr",
            contact_phone="0123456789",
            enterprise_code="1234",
            activity_category_code="abcd1234",
            representative="Mister Example",
            representative_profession="Educational representative",
            signatory_representative="Big boss",
            signatory_representative_profession="Director",
        )
        factories.OrganizationAddressFactory(
            organization=organization,
            owner=None,
            is_main=True,
            is_reusable=True,
        )
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product=factories.ProductFactory(
                contract_definition=factories.ContractDefinitionFactory(
                    title="CONTRACT DEFINITION 4",
                    description="Contract definition description",
                    body="""
                    ## Articles de la convention

                    ## Terms and conditions
                    Terms and conditions content
                    """,
                    language="fr-fr",
                ),
                title="You will know that you know you don't know",
                price="999.99",
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
            ),
            course=factories.CourseFactory(
                organizations=[organization],
                effort=timedelta(hours=10, minutes=30, seconds=12),
            ),
        )
        order = factories.OrderFactory(
            owner=user,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_VALIDATED,
            main_invoice=InvoiceFactory(recipient_address=user_address),
        )
        factories.ContractFactory(order=order)
        factories.OrderTargetCourseRelationFactory(
            course=relation.course, order=order, position=1
        )
        context = contract_definition.generate_document_context(
            contract_definition=order.contract.definition,
            user=user,
            order=order,
        )
        context["syllabus"] = "Syllabus Test"
        mock_processor_for_test.assert_called_once_with(context)

        file_bytes = issuers.generate_document(
            name=order.contract.definition.name,
            context=context,
        )
        document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")

        self.assertEqual(
            context["extra"],
            {
                "course_code": relation.course.code,
                "language_code": "fr-fr",
                "is_for_test": True,
            },
        )
        self.assertRegex(document_text, r"John Doe")
        self.assertRegex(document_text, r"Terms and conditions")
        self.assertRegex(document_text, r"Session start date")
        self.assertRegex(document_text, r"01/01/2024 9 a.m.")
        self.assertRegex(document_text, r"Session end date")
        self.assertRegex(document_text, r"03/31/2024 6 p.m")
        self.assertRegex(document_text, r"Price of the course")
        self.assertRegex(document_text, r"999.99 €")
        self.assertRegex(document_text, r"Appendices")
        self.assertRegex(document_text, r"Syllabus Test")
        self.assertRegex(document_text, r"[SignatureField#1]")
        self.assertRegex(document_text, r"[SignatureField#2]")
