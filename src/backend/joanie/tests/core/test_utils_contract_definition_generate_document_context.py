"""Test suite for `generate_document_context` utility"""
from django.test import TestCase

from joanie.core import factories
from joanie.core.utils import contract_definition, image_to_base64
from joanie.payment.factories import InvoiceFactory


class UtilsGenerateDocumentContextTestCase(TestCase):
    """Test suite for `generate_document_context` utility"""

    def test_utils_contract_definition_generate_document_context_with_order(self):
        """
        When we generate the document context for a contract definition with an order, it should
        return a context with all the data attached to the contract definition, the user and
        the order.
        """
        user = factories.UserFactory(
            email="student@exmaple.fr", first_name="John Doe", last_name=""
        )
        address = factories.AddressFactory(
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
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(
                contract_definition=factories.ContractDefinitionFactory(
                    title="CONTRACT DEFINITION 1", body="Articles de la convention"
                )
            ),
        )
        InvoiceFactory(order=order, recipient_address=address)
        definition = order.product.contract_definition
        expected_context = {
            "contract": {
                "body": "<p>Articles de la convention</p>",
                "title": "CONTRACT DEFINITION 1",
            },
            "course": {
                "name": order.product.title,
            },
            "student": {
                "name": user.get_full_name(),
                "address": {
                    "address": "5 Rue de L'Exemple",
                    "city": "Paris",
                    "country": "FR",
                    "first_name": "John",
                    "last_name": "Doe",
                    "id": str(address.id),
                    "is_main": False,
                    "postcode": "75000",
                    "title": "Office",
                },
            },
            "organization": {
                "logo": image_to_base64(order.organization.logo),
                "name": order.organization.title,
                "signature": image_to_base64(order.organization.signature),
            },
        }

        context = contract_definition.generate_document_context(
            contract_definition=definition, user=user, order=order
        )

        self.assertDictEqual(context, expected_context)

    def test_utils_contract_definition_generate_document_context_without_order(self):
        """
        When we generate the document context for a contract definition without an order and
        the user's address, it should return default values for the keys :
        `course.name`, `organization.logo`, `organization.signature`, `organization.title`.
        """
        organization_fallback_logo = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
            "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
        )
        user = factories.UserFactory(
            email="student@exmaple.fr", first_name="John Doe", last_name=""
        )
        definition = factories.ContractDefinitionFactory(
            title="CONTRACT DEFINITION 2", body="Articles de la convention"
        )
        expected_context = {
            "contract": {
                "body": "<p>Articles de la convention</p>",
                "title": "CONTRACT DEFINITION 2",
            },
            "course": {
                "name": "<COURSE_NAME>",
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
                    "title": "",
                },
            },
            "organization": {
                "logo": organization_fallback_logo,
                "name": "<ORGANIZATION_NAME>",
                "signature": organization_fallback_logo,
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
        When we generate the document context for the contract definition without : an order and
        an address, it should return the default placeholder values for the fields :
        `course.name`, `student.address`, `organization.logo`, `organization.signature`,
        `organization.title`.
        """
        organization_fallback_logo = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
            "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
        )
        student_fallback_address = {
            "address": "<STUDENT_ADDRESS_STREET_NAME>",
            "city": "<STUDENT_ADDRESS_CITY>",
            "country": "<STUDENT_ADDRESS_COUNTRY>",
            "last_name": "<STUDENT_LAST_NAME>",
            "first_name": "<STUDENT_FIRST_NAME>",
            "postcode": "<STUDENT_ADDRESS_POSTCODE>",
            "title": "",
        }
        user = factories.UserFactory(
            email="student@exmaple.fr", first_name="John Doe", last_name=""
        )
        definition = factories.ContractDefinitionFactory(
            title="CONTRACT DEFINITION 2", body="Articles de la convention"
        )
        expected_context = {
            "contract": {
                "body": "<p>Articles de la convention</p>",
                "title": "CONTRACT DEFINITION 2",
            },
            "course": {
                "name": "<COURSE_NAME>",
            },
            "student": {
                "name": user.get_full_name(),
                "address": student_fallback_address,
            },
            "organization": {
                "logo": organization_fallback_logo,
                "name": "<ORGANIZATION_NAME>",
                "signature": organization_fallback_logo,
            },
        }

        context = contract_definition.generate_document_context(
            contract_definition=definition, user=user
        )

        self.assertDictEqual(context, expected_context)
