"""Test suite for `generate_document_context` utility"""
from django.contrib.sites.models import Site
from django.test import TestCase

from joanie.core import enums, factories
from joanie.core.utils import contract_definition, image_to_base64
from joanie.payment.factories import InvoiceFactory


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
            organization=organization, is_main=True, is_reusable=True
        )
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(
                title="CONTRACT DEFINITION 1",
                description="Contract definition description",
                body="Articles de la convention",
            ),
            course=factories.CourseFactory(organizations=[organization]),
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
        freezed_course_data = order.get_equivalent_course_run_dates()
        expected_context = {
            "contract": {
                "body": "<p>Articles de la convention</p>",
                "terms_and_conditions": "<h2>Terms and conditions</h2>",
                "description": "Contract definition description",
                "title": "CONTRACT DEFINITION 1",
            },
            "course": {
                "name": order.product.title,
                "code": relation.course.code,
                "start": freezed_course_data["start"],
                "end": freezed_course_data["end"],
                "effort": order.course.effort,
                "price": order.total,
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

        self.assertDictEqual(context, expected_context)

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
        )
        expected_context = {
            "contract": {
                "body": "<p>Articles de la convention</p>",
                "terms_and_conditions": "",
                "description": "Contract definition description",
                "title": "CONTRACT DEFINITION 2",
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
        )
        expected_context = {
            "contract": {
                "body": "<p>Articles de la convention</p>",
                "terms_and_conditions": "",
                "description": "Contract definition description",
                "title": "CONTRACT DEFINITION 3",
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
