"""Test suite for the management command 'generate_zip_archive_of_contracts'"""
import uuid
from io import BytesIO
from zipfile import ZipFile

from django.core.files.storage import default_storage
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories
from joanie.core.utils import contract_definition, issuers


class GenerateZipArchiveOfContractsCommandTestCase(TestCase):
    """Test case for the management command 'generate_zip_archive_of_contracts'"""

    def setUp(self):
        default_storage.delete("signed_contracts.zip")

    def test_commands_generate_zip_archive_contracts_fails_without_parameter(
        self,
    ):
        """
        This command should accept one parameter: courses product relation UUID.
        If the parameter is missing, the command should raise an error.
        """
        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts")

        self.assertEqual(
            str(context.exception),
            "The required parameter `course_product_relation` uuid is missing.",
        )

    def test_commands_generate_zip_archive_contracts_fails_courseproductrelation_does_not_exist(
        self,
    ):
        """
        This command should accept one argument: courses product relation UUID.
        If the given UUID of the object does not exist, it should raise an error.
        """
        options = {
            "course_product_relation": uuid.uuid4(),
        }

        with self.assertRaises(ValueError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            "Make sure to give an existing course product relation.",
        )

    def test_commands_generate_zip_archive_contracts_aborts_because_no_signed_contracts_yet(
        self,
    ):
        """
        This command should accept one argument: a course product relation UUID.
        If the given UUID of the object exists but has no contracts that are signed,
        it should return an error.
        """
        users = factories.UserFactory.create_batch(3)
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        course_product_relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        options = {
            "course_product_relation": course_product_relation.pk,
        }
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        files_in_bytes = []
        for index, reference in enumerate(signature_reference_choices):
            user = users[index]
            order = factories.OrderFactory(
                owner=user,
                product=course_product_relation.product,
                course=course_product_relation.course,
                state=enums.ORDER_STATE_PENDING,
            )
            context = contract_definition.generate_document_context(
                order.product.contract_definition, user, order
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context=context,
                submitted_for_signature_on=timezone.now(),
            )
            pdf_bytes_file = issuers.generate_document(
                order.product.contract_definition.name, context=context
            )
            files_in_bytes.append(pdf_bytes_file)

        with self.assertRaises(ValueError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            "There are no signed contract attached to the course product relation object.",
        )

    # pylint: disable=too-many-locals
    def test_commands_generate_zip_archive_contracts_success(
        self,
    ):
        """
        This command should accept one argument: a course product relation UUID.
        If the given UUID of the object exists, then it should store the ZIP archive in
        the default storage. We make sure that the ZIP archive is accessible in default storage
        through its filename.
        """
        users = factories.UserFactory.create_batch(3)
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        course_product_relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        options = {
            "course_product_relation": course_product_relation.pk,
        }
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        files_in_bytes = []
        for index, reference in enumerate(signature_reference_choices):
            user = users[index]
            order = factories.OrderFactory(
                owner=user,
                product=course_product_relation.product,
                course=course_product_relation.course,
                state=enums.ORDER_STATE_VALIDATED,
            )
            context = contract_definition.generate_document_context(
                order.product.contract_definition, user, order
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context=context,
                signed_on=timezone.now(),
            )
            pdf_bytes_file = issuers.generate_document(
                order.product.contract_definition.name, context=context
            )
            files_in_bytes.append(pdf_bytes_file)

        call_command("generate_zip_archive_of_contracts", **options)

        # Retrieve the ZIP archive from default storage
        with default_storage.open(
            "signed_contracts_extract.zip"
        ) as storage_zip_archive:
            with ZipFile(storage_zip_archive, "r") as zip_archive:
                file_names = zip_archive.namelist()
                # Check the amount of files inside the ZIP archive
                self.assertEqual(len(file_names), 3)
                # Check the file name of each pdf in bytes
                for index, pdf_filename in enumerate(file_names):
                    self.assertEqual(pdf_filename, f"contract_{index}.pdf")
                    # Check the content of the PDF inside the ZIP archive
                    with zip_archive.open(pdf_filename) as pdf_file:
                        document_text = pdf_extract_text(
                            BytesIO(pdf_file.read())
                        ).replace("\n", "")

                        self.assertRegex(document_text, r"CONTRACT")
                        self.assertRegex(document_text, r"DEFINITION")
                        self.assertRegex(
                            document_text, r"1 Rue de L'Exemple 75000, Paris."
                        )
