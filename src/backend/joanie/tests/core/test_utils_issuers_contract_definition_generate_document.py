"""Test suite for utility method to generate document of Contract Definition in PDF bytes format"""
from io import BytesIO

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

    def test_utils_contract_definition_generate_document(self):
        """
        Issuer 'generate document' method should generate a contract definition document.
        """
        user = factories.UserFactory(
            email="student@example.fr", first_name="John", last_name="Doe"
        )
        address = factories.AddressFactory(
            owner=user,
            address="1 Rue de L'Exemple",
            postcode="75000",
            city="Paris",
            is_reusable=False,
            title="Office",
            country="FR",
        )
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
            state=enums.ORDER_STATE_VALIDATED,
            main_invoice=InvoiceFactory(recipient_address=address),
        )
        contract = factories.ContractFactory(order=order)
        file_bytes = issuers.generate_document(
            name=contract.definition.name,
            context=contract_definition_utility.generate_document_context(
                contract_definition=contract.definition, user=user, order=contract.order
            ),
        )
        document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")

        self.assertRegex(document_text, r"John Doe")
        self.assertRegex(document_text, r"1 Rue de L'Exemple 75000, Paris")
        self.assertRegex(document_text, r"Student's signature")
        self.assertRegex(document_text, r"Representative's signature")
        self.assertRegex(document_text, r"Your order is delivered by the organization")
