"""Test suite for the management command `generate_zip_archive_of_contracts`"""
import random
from io import BytesIO, StringIO
from uuid import uuid4
from zipfile import ZipFile

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories
from joanie.core.utils import contract_definition


class GenerateZipArchiveOfContractsCommandTestCase(TestCase):
    """Test case for the management command `generate_zip_archive_of_contracts`"""

    def test_commands_generate_zip_archive_contracts_fails_without_parameters(self):
        """
        This command must have a User UUID to be executed, else the command aborts.
        """
        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts")

        self.assertEqual(
            str(context.exception),
            "You must provide a User UUID for the command because it's required.",
        )

    def test_commands_generate_zip_archive_contracts_fails_without_user_uuid_parameter_only(
        self,
    ):
        """
        If the command has no User UUID as input parameter but has one of both optional parameters
        (course product relation UUID or an organization UUID) set, it should raise an error.
        """
        random_organization_uuid = uuid4()
        options = {
            "organization": random_organization_uuid,
        }

        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            "You must provide a User UUID for the command because it's required.",
        )

    def test_commands_generate_zip_archive_contracts_fails_with_user_uuid_parameter_only(
        self,
    ):
        """
        This command should accept one out of the two required parameters which are:
        a Course Product Relation UUID or an Organition UUID. When the user is declared but
        both optional parameters are missing, the command should raise an error.
        """
        user = factories.UserFactory()
        options = {"user": user.pk}

        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            "You must to provide at least one of the two required parameters. "
            "It can be a Course Product Relation UUID, or an Organization UUID.",
        )

    def test_commands_generate_zip_archive_contracts_fails_courseproductrelation_does_not_exist(
        self,
    ):
        """
        Generating a ZIP archive of contract from an unknown Course Product Relation UUID should
        raise an error.
        """
        user = factories.UserFactory()
        random_course_product_relation_uuid = uuid4()
        options = {
            "user": user.pk,
            "course_product_relation": random_course_product_relation_uuid,
        }

        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            "Make sure to give an existing course product relation UUID. "
            "No CourseProductRelation was found with the given "
            f"UUID : {random_course_product_relation_uuid}.",
        )

    def test_commands_generate_zip_archive_contracts_fails_organization_does_not_exist(
        self,
    ):
        """
        Generating a ZIP archive of contract from an unknown Organization UUID should raise an
        error.
        """
        user = factories.UserFactory()
        random_organization_uuid = uuid4()
        options = {
            "user": user.pk,
            "organization": random_organization_uuid,
        }

        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            "Make sure to give an existing organization UUID. "
            f"No Organization was found with the givin UUID : {random_organization_uuid}.",
        )

    def test_commands_generate_zip_archive_contracts_aborts_because_no_signed_contracts_yet(
        self,
    ):
        """
        From an existing Course Product Relation UUID, but there are no signed contracts,
        it should raise an error mentionning that it has to abort in generating the ZIP archive.
        """
        users = factories.UserFactory.create_batch(3)
        requesting_user = factories.UserFactory()
        relation = factories.CourseProductRelationFactory()
        options = random.choice(
            [
                {
                    "user": requesting_user.pk,
                    "course_product_relation": relation.pk,
                },
                {
                    "user": requesting_user.pk,
                    "organization": relation.organizations.first().pk,
                },
            ]
        )
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, reference in enumerate(signature_reference_choices):
            user = users[index]
            order = factories.OrderFactory(
                owner=user,
                product=relation.product,
                course=relation.course,
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

        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            "There are no signed contracts with the given parameter. "
            "Abort generating ZIP archive.",
        )

    def test_commands_generate_zip_archive_contracts_success_with_courseproductrelation_parameter(
        self,
    ):  # pylint: disable=too-many-locals
        """
        From an existing Course Product Relation UUID paired with an existing User UUID,
        we should be able to fetch signed contracts attached to generate a ZIP archive.
        Then, the ZIP archive is saved into the file system storage. Then, we make sure the ZIP
        archive is accessible when fetching it from the file system storage with its filename.
        Finally, we iterate over each accessible files.
        """
        command_output = StringIO()
        file_storage = FileSystemStorage(
            location=settings.STORAGES.get("contracts").get("OPTIONS").get("location")
        )
        users = factories.UserFactory.create_batch(3)
        requesting_user = factories.UserFactory()
        relation = factories.CourseProductRelationFactory()
        zip_uuid = uuid4()
        options = {
            "user": requesting_user.pk,
            "course_product_relation": relation.pk,
            "zip": zip_uuid,
        }
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, reference in enumerate(signature_reference_choices):
            user = users[index]
            order = factories.OrderFactory(
                owner=user,
                product=relation.product,
                course=relation.course,
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

        call_command(
            "generate_zip_archive_of_contracts", stdout=command_output, **options
        )

        zipfile_filename = command_output.getvalue().splitlines()
        self.assertEqual(zipfile_filename, [f"{requesting_user.pk}_{zip_uuid}.zip"])

        # Retrieve the ZIP archive from file system storage
        zipfile_file = zipfile_filename[0]
        with file_storage.open(zipfile_file) as file_storage_zip_archive:
            with ZipFile(file_storage_zip_archive, "r") as zip_archive:
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
        # Clear file zip archive in data/contracts
        file_storage.delete(zipfile_file)

    def test_commands_generate_zip_archive_contracts_success_with_organization_parameter(
        self,
    ):  # pylint: disable=too-many-locals
        """
        From an existing Organization UUID paired with an existing User UUID, we should be
        able to fetch the signed contracts attached to generate a ZIP archive. Then, the ZIP
        archive is saved into the file system storage. We check that the input parameter of the ZIP
        UUID is used into the filename. We make sure that the ZIP archive is accessible when
        fetching it from the file system storage with its filename. Finally, we iterate over each
        accessible files.
        """
        command_output = StringIO()
        file_storage = FileSystemStorage(
            location=settings.STORAGES.get("contracts").get("OPTIONS").get("location")
        )
        users = factories.UserFactory.create_batch(3)
        requesting_user = factories.UserFactory()
        relation = factories.CourseProductRelationFactory()
        organization = relation.organizations.first()
        zip_uuid = uuid4()
        options = {
            "user": requesting_user.pk,
            "organization": organization.pk,
            "zip": zip_uuid,
        }
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, reference in enumerate(signature_reference_choices):
            user = users[index]
            order = factories.OrderFactory(
                owner=user,
                product=relation.product,
                course=relation.course,
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

        call_command(
            "generate_zip_archive_of_contracts", stdout=command_output, **options
        )
        zipfile_filename = command_output.getvalue().splitlines()
        # Check that the given ZIP UUID is used into the filename
        self.assertEqual(zipfile_filename, [f"{requesting_user.pk}_{zip_uuid}.zip"])

        # Retrieve the ZIP archive from file system storage
        zipfile_file = zipfile_filename[0]
        with file_storage.open(zipfile_file) as file_storage_zip_archive:
            with ZipFile(file_storage_zip_archive, "r") as zip_archive:
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
        # Clear file zip archive in data/contracts
        file_storage.delete(zipfile_file)

    def test_commands_generate_zip_archive_with_too_long_zip_uuid_input_parameter(self):
        """
        Generating a ZIP archive and parsing a value over 36 characters for the ZIP UUID
        parameter, the command should generate one itself. We should find another value in
        the output of the command to generate a ZIP archive.
        """
        command_output = StringIO()
        file_storage = FileSystemStorage(
            location=settings.STORAGES.get("contracts").get("OPTIONS").get("location")
        )
        user = factories.UserFactory()
        requesting_user = factories.UserFactory()
        relation = factories.CourseProductRelationFactory()
        organization = relation.organizations.first()
        zip_uuid = "aH3kRj2ZvXo5Nt1wPq9SbYp4Q8sU6W2G3eL7ia"  # 38 characters long
        options = random.choice(
            [
                {
                    "user": requesting_user.pk,
                    "organization": organization.pk,
                    "zip": zip_uuid,
                },
                {
                    "user": requesting_user.pk,
                    "course_product_relation": relation.pk,
                    "zip": zip_uuid,
                },
            ]
        )
        order = factories.OrderFactory(
            owner=user,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        context = contract_definition.generate_document_context(
            order.product.contract_definition, user, order
        )
        factories.ContractFactory(
            order=order,
            signature_backend_reference="wfl_fake_dummy_1",
            definition_checksum="1234",
            context=context,
            signed_on=timezone.now(),
        )

        call_command(
            "generate_zip_archive_of_contracts", stdout=command_output, **options
        )

        zipfile_filename = command_output.getvalue().splitlines()
        parts = zipfile_filename[0].split("_")
        zip_uuid_found = parts[1].split(".")[0]

        self.assertEqual(len(str(zip_uuid_found)), 36)
        self.assertNotEqual(zip_uuid_found, zip_uuid)
        self.assertEqual(zipfile_filename, [f"{requesting_user.pk}_{zip_uuid_found}.zip"])
        self.assertNotEqual(zipfile_filename, [f"{requesting_user.pk}_{zip_uuid}.zip"])
        # Clear the file system storage
        file_storage.delete(zipfile_filename[0])

    def test_commands_generate_zip_archive_with_zip_uuid_input_parameter_with_underscores(
        self,
    ):
        """
        Generating a ZIP archive and parsing a value of 36 characters for the ZIP UUID
        parameter when it contains "_" (underscore), the command will clean this input parameter
        and replace every "_" by "-". We should find a value in the output with this replacement.
        """
        command_output = StringIO()
        file_storage = FileSystemStorage(
            location=settings.STORAGES.get("contracts").get("OPTIONS").get("location")
        )
        user = factories.UserFactory()
        requesting_user = factories.UserFactory()
        relation = factories.CourseProductRelationFactory()
        organization = relation.organizations.first()
        zip_uuid = "2a4f1d23_f5eb_4044_bbdc_1fbc2df23f3a"
        expected_zip_uuid_output_in_filename = "2a4f1d23-f5eb-4044-bbdc-1fbc2df23f3a"
        options = {
            "user": requesting_user.pk,
            "organization": organization.pk,
            "zip": zip_uuid,
        }
        order = factories.OrderFactory(
            owner=user,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_VALIDATED,
        )
        context = contract_definition.generate_document_context(
            order.product.contract_definition, user, order
        )
        factories.ContractFactory(
            order=order,
            signature_backend_reference="wfl_fake_dummy_1",
            definition_checksum="1234",
            context=context,
            signed_on=timezone.now(),
        )

        call_command(
            "generate_zip_archive_of_contracts", stdout=command_output, **options
        )

        zipfile_filename = command_output.getvalue().splitlines()

        self.assertNotEqual(
            zipfile_filename,
            ([f"{requesting_user.pk}_{zip_uuid}.zip"]),
        )
        self.assertEqual(
            zipfile_filename,
            ([f"{requesting_user.pk}_{expected_zip_uuid_output_in_filename}.zip"]),
        )
        # Clear the file system storage
        file_storage.delete(zipfile_filename[0])
