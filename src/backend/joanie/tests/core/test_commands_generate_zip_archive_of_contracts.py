"""Test suite for the management command `generate_zip_archive_of_contracts`"""
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
    """Test case for the management command `generate_zip_archive_of_contracts`"""

    def setUp(self):
        default_storage.delete("signed_contracts.zip")

    def test_commands_generate_zip_archive_contracts_fails_without_required_parameters(
        self,
    ):
        """
        This command should accept one out of the two required parameters which are:
        a course product relation UUID or an orgzanition UUID.
        If the both parameter are missing, the command should raise an error.
        """
        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts")

        self.assertEqual(
            str(context.exception),
            "You need to provide at least one of the two required parameters. "
            "It can be a Course Product Relation UUID, or an Organization UUID.",
        )

    def test_commands_generate_zip_archive_contracts_fails_courseproductrelation_does_not_exist(
        self,
    ):
        """
        Generating a zip archive of contract from an unknown course product relation UUID should
        raise an error.
        """
        random_course_product_relation_uuid = uuid.uuid4()
        options = {
            "course_product_relation": random_course_product_relation_uuid,
        }

        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            "Make sure to give an existing course product relation uuid. "
            "No CourseProductRelation was found with the given "
            f"UUID : {random_course_product_relation_uuid}.",
        )

    def test_commands_generate_zip_archive_contracts_fails_organization_does_not_exist(
        self,
    ):
        """
        Generating a zip archive of contract from an unknown organization UUID should raise an
        error.
        """
        random_organization_uuid = uuid.uuid4()
        options = {
            "organization": random_organization_uuid,
        }

        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            "Make sure to give an existing organization uuid. "
            f"No Organization was found with the givin UUID : {random_organization_uuid}.",
        )

    def test_commands_generate_zip_archive_contracts_aborts_because_no_signed_contracts_yet(
        self,
    ):
        """
        When we parse a course product relation UUID, but there are no signed contracts yet,
        it should raise an error mentionning that it has to abort generating the ZIP archive.
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
                submitted_for_signature_on=timezone.now(),
            )
            pdf_bytes_file = issuers.generate_document(
                order.product.contract_definition.name, context=context
            )
            files_in_bytes.append(pdf_bytes_file)

        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            "There are no signed contracts with the given parameter. "
            "Abort generating ZIP archive.",
        )

    # pylint: disable=too-many-locals
    def test_commands_generate_zip_archive_contracts_success_with_courseproductrelation_parameter(
        self,
    ):
        """
        When we parse a course product relation UUID and the object exists, we should be able
        to fetch the signed contracts attached to generate a ZIP archive. Then, the ZIP
        archive is saved into the default storage. We make sure that the ZIP archive is accessible
        when retrieving in default storage with its filename.
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

    def test_commands_generate_zip_archive_contracts_success_with_organization_parameter(
        self,
    ):
        """
        When we parse an organization UUID and the object exists, we should be able to fetch
        the signed contracts attached to generate a ZIP archive. Then, the ZIP archive is saved
        into the default storage. We make sure that the ZIP archive is accessible when retrieving
        in default storage with its filename.
        """
        users = factories.UserFactory.create_batch(3)
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        course_product_relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        organization = course_product_relation.organizations.all().first()
        options = {
            "organization": organization.pk,
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
