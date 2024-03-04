"""Tests for the Contract Definition Model"""

from django.test import TestCase

from joanie.core import factories


class ContractDefinitionModelTestCase(TestCase):
    """
    Contract Definition Model test case.
    """

    def test_models_contract_definition_get_body_in_html_with_empty_body(self):
        """
        We should get an empty string in return when we call the get body in HTML method
        if the contract definition body is empty.
        """
        contract_definition = factories.ContractDefinitionFactory(
            title="Contract Definition 1", body=""
        )

        result = contract_definition.get_body_in_html()

        self.assertEqual(result, "")

    def test_models_contract_definition_get_body_in_html(self):
        """
        We should get the HTML format of the markdown content of the contract definition body
        when we call get body in HTML method.
        """
        content = "## The student must have a computer to follow the course"
        expected_html = "<h2>The student must have a computer to follow the course</h2>"
        contract_definition = factories.ContractDefinitionFactory(
            title="Contract Definition 1", body=content
        )

        result = contract_definition.get_body_in_html()

        self.assertEqual(result, expected_html)
