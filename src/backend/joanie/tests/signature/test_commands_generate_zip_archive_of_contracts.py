"""Test suite for the management command `generate_zip_archive_of_contracts`"""

import random
from io import BytesIO, StringIO
from uuid import uuid4
from zipfile import ZipFile

from django.core.files.storage import storages
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories
from joanie.core.utils import contract_definition
from joanie.payment import factories as payment_factories


class GenerateZipArchiveOfContractsCommandTestCase(TestCase):
    """Test case for the management command `generate_zip_archive_of_contracts`"""

    maxDiff = None

    def test_commands_generate_zip_archive_contracts_fails_without_parameters(self):
        """
        The command must have a User UUID to be executed, else the command aborts.
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
        (offering UUID or an organization UUID) set, it should raise an error.
        """
        random_organization_uuid = uuid4()
        options = {
            "organization_id": random_organization_uuid,
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
        The command should accept one out of the two required parameters which are:
        an offering UUID or an Organition UUID. When the user is declared but
        both optional parameters are missing, the command should raise an error.
        """
        user = factories.UserFactory()
        options = {"user": user.pk}

        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            str(
                {
                    "non_field_errors": (
                        "You must set at least one parameter for the method."
                        "You must choose between an Organization UUID or an Offering UUID."
                    )
                }
            ),
        )

    def test_commands_generate_zip_archive_contracts_fails_courseproductrelation_does_not_exist(
        self,
    ):
        """
        Generating a ZIP archive of contract from an unknown offering UUID should
        raise an error.
        """
        user = factories.UserFactory()
        random_offering_uuid = uuid4()
        options = {
            "user": user.pk,
            "offering_id": random_offering_uuid,
        }
        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            str(
                {
                    "offering_id": (
                        "Make sure to give an existing offering UUID. "
                        "No CourseProductRelation was found with the given "
                        f"UUID : {random_offering_uuid}."
                    ),
                }
            ),
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
            "organization_id": random_organization_uuid,
        }

        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            str(
                {
                    "organization_id": (
                        "Make sure to give an existing organization UUID. "
                        "No Organization was found with the given UUID : "
                        f"{random_organization_uuid}."
                    )
                }
            ),
        )

    def test_commands_generate_zip_archive_contracts_fails_because_user_does_not_have_org_access(
        self,
    ):
        """
        Generating a ZIP archive of contracts for a User who does not have access rights
        to the Organization that is providing the offering, it should raise
        an error.
        """
        users = factories.UserFactory.create_batch(3)
        requesting_user = factories.UserFactory()
        # Organization that is not a the course or product supplier
        factories.UserOrganizationAccessFactory(user=requesting_user)
        organization_course_provider = factories.OrganizationFactory()
        offering = factories.OfferingFactory(
            organizations=[organization_course_provider],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        options = random.choice(
            [
                {
                    "user": requesting_user.pk,
                    "offering_id": offering.pk,
                },
                {
                    "user": requesting_user.pk,
                    "organization_id": offering.organizations.first().pk,
                },
            ]
        )
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
        ]
        for index, reference in enumerate(signature_reference_choices):
            user = users[index]
            order = factories.OrderFactory(
                owner=user,
                product=offering.product,
                course=offering.course,
                state=enums.ORDER_STATE_COMPLETED,
                main_invoice=payment_factories.InvoiceFactory(),
            )
            context = contract_definition.generate_document_context(
                order.product.contract_definition, user, order
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context=context,
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )

        with self.assertRaises(CommandError) as context:
            call_command("generate_zip_archive_of_contracts", **options)

        self.assertEqual(
            str(context.exception),
            "There are no signed contracts with the given parameter. "
            "Abort generating ZIP archive.",
        )

    def test_commands_generate_zip_archive_contracts_aborts_because_no_signed_contracts_yet(
        self,
    ):
        """
        From an existing offering UUID and a User who has the access rights on the
        organization, when there are no signed contracts yet, it should raise an error mentionning
        that it has to abort in generating the ZIP archive.
        """
        users = factories.UserFactory.create_batch(3)
        requesting_user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            organization=organization, user=requesting_user
        )
        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        options = random.choice(
            [
                {
                    "user": requesting_user.pk,
                    "offering_id": offering.pk,
                },
                {
                    "user": requesting_user.pk,
                    "organization_id": offering.organizations.first().pk,
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
                product=offering.product,
                course=offering.course,
                state=enums.ORDER_STATE_COMPLETED,
                main_invoice=payment_factories.InvoiceFactory(),
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
        From an existing offering UUID paired with an existing User UUID who has
        the correct access right on the organization, we should be able to fetch signed contracts
        that are attached to generate a ZIP archive.
        Then, the ZIP archive is saved into the file system storage. After, we make sure the ZIP
        archive is accessible from the file system storage with its filename. Finally, we iterate
        over each accessible files.
        """
        command_output = StringIO()
        storage = storages["contracts"]
        users = factories.UserFactory.create_batch(3)
        requesting_user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            organization=organization, user=requesting_user
        )
        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(
                title="Contract definition 0"
            ),
        )
        zip_uuid = uuid4()
        options = {
            "user": requesting_user.pk,
            "offering_id": offering.pk,
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
                product=offering.product,
                course=offering.course,
                state=enums.ORDER_STATE_COMPLETED,
                main_invoice=payment_factories.InvoiceFactory(
                    recipient_address__address="1 Rue de L'Exemple",
                    recipient_address__postcode=75000,
                    recipient_address__city="Paris",
                    recipient_address__country="FR",
                ),
            )
            context = contract_definition.generate_document_context(
                order.product.contract_definition, user, order
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context=context,
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )

        call_command(
            "generate_zip_archive_of_contracts", stdout=command_output, **options
        )

        zip_archive_name = command_output.getvalue().splitlines()
        self.assertEqual(zip_archive_name, [f"{requesting_user.pk}_{zip_uuid}.zip"])

        zip_archive = zip_archive_name[0]
        # Retrieve the ZIP archive from storages
        with storage.open(zip_archive) as storage_zip_archive:
            with ZipFile(storage_zip_archive, "r") as zip_archive_elements:
                file_names = zip_archive_elements.namelist()
                # Check the amount of files inside the ZIP archive
                self.assertEqual(len(file_names), 3)
                # Check the file name of each pdf in bytes
                for index, pdf_filename in enumerate(file_names):
                    self.assertEqual(pdf_filename, f"contract_{index}.pdf")
                    # Check the content of the PDF inside the ZIP archive
                    with zip_archive_elements.open(pdf_filename) as pdf_file:
                        document_text = pdf_extract_text(
                            BytesIO(pdf_file.read())
                        ).replace("\n", "")

                        self.assertIn("Contract definition 0", document_text)
                        self.assertIn(
                            "1 Rue de L'Exemple, 75000 Paris (FR)", document_text
                        )

        # Clear ZIP archive in storages
        storage.delete(zip_archive)

    def test_commands_generate_zip_archive_contracts_success_with_organization_parameter(
        self,
    ):  # pylint: disable=too-many-locals
        """
        From an existing Organization UUID paired with an existing User UUID who has the correct
        access rights for an organization, we should be able to fetch the signed contracts that are
        attached to generate a ZIP archive.
        Then, the ZIP archive is saved into the file system storage. We check that the input
        parameter of the ZIP UUID is used into the filename. We make sure that the ZIP archive is
        accessible from the file system storage under its filename. Finally, we iterate over each
        accessible files.
        """
        command_output = StringIO()
        storage = storages["contracts"]
        users = factories.UserFactory.create_batch(3)
        requesting_user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            organization=organization, user=requesting_user
        )
        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(
                title="Contract definition 0"
            ),
        )
        zip_uuid = uuid4()
        options = {
            "user": requesting_user.pk,
            "organization_id": organization.pk,
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
                product=offering.product,
                course=offering.course,
                state=enums.ORDER_STATE_COMPLETED,
                main_invoice=payment_factories.InvoiceFactory(
                    recipient_address__address="1 Rue de L'Exemple",
                    recipient_address__postcode=75000,
                    recipient_address__city="Paris",
                    recipient_address__country="FR",
                ),
            )
            context = contract_definition.generate_document_context(
                order.product.contract_definition, user, order
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context=context,
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )

        call_command(
            "generate_zip_archive_of_contracts", stdout=command_output, **options
        )

        zip_archive_name = command_output.getvalue().splitlines()
        # Check that the given ZIP UUID is used into the filename
        self.assertEqual(zip_archive_name, [f"{requesting_user.pk}_{zip_uuid}.zip"])

        zip_archive = zip_archive_name[0]
        # Retrieve the ZIP archive from storages
        with storage.open(zip_archive) as storage_zip_archive:
            with ZipFile(storage_zip_archive, "r") as zip_archive_elements:
                file_names = zip_archive_elements.namelist()
                # Check the amount of files inside the ZIP archive
                self.assertEqual(len(file_names), 3)
                # Check the file name of each pdf in bytes
                for index, pdf_filename in enumerate(file_names):
                    self.assertEqual(pdf_filename, f"contract_{index}.pdf")
                    # Check the content of the PDF inside the ZIP archive
                    with zip_archive_elements.open(pdf_filename) as pdf_file:
                        document_text = pdf_extract_text(
                            BytesIO(pdf_file.read())
                        ).replace("\n", "")

                        self.assertIn("Contract definition 0", document_text)
                        self.assertIn(
                            "1 Rue de L'Exemple, 75000 Paris (FR)", document_text
                        )

        # Clear ZIP archive in storages
        storage.delete(zip_archive)

    def test_commands_generate_zip_archive_with_parameter_zip_uuid_is_not_a_uuid_structure(
        self,
    ):
        """
        Generating a ZIP archive and parsing a value over 36 characters for the ZIP UUID
        parameter, the command should generate one itself. We should find another value in
        the output of the command to generate a ZIP archive.
        """
        command_output = StringIO()
        storage = storages["contracts"]
        user = factories.UserFactory()
        requesting_user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            organization=organization, user=requesting_user
        )
        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        zip_uuid = random.choice(
            [
                "aH3kRj2ZvXo5Nt1wPq9SbYp4Q8sU6W2G3eL7ia",  # 38 characters long
                "aH3kRj2_vXo5N_1wPq9_bYp4Q_sU6W_G3eL7"  # with underscore,
                "1234-4567"  # short string
                "abc-defg-hijklm-nopqrst",  # only alphabetic letters
            ]
        )
        options = random.choice(
            [
                {
                    "user": requesting_user.pk,
                    "organization_id": organization.pk,
                    "zip": zip_uuid,
                },
                {
                    "user": requesting_user.pk,
                    "offering_id": offering.pk,
                    "zip": zip_uuid,
                },
            ]
        )
        order = factories.OrderFactory(
            owner=user,
            product=offering.product,
            course=offering.course,
            state=enums.ORDER_STATE_COMPLETED,
            main_invoice=payment_factories.InvoiceFactory(),
        )
        context = contract_definition.generate_document_context(
            order.product.contract_definition, user, order
        )
        factories.ContractFactory(
            order=order,
            signature_backend_reference="wfl_fake_dummy_1",
            definition_checksum="1234",
            context=context,
            student_signed_on=timezone.now(),
            organization_signed_on=timezone.now(),
        )

        call_command(
            "generate_zip_archive_of_contracts", stdout=command_output, **options
        )

        zip_archive_name = command_output.getvalue().splitlines()
        parts = zip_archive_name[0].split("_")
        zip_uuid_found = parts[1].split(".")[0]

        self.assertEqual(len(str(zip_uuid_found)), 36)
        self.assertNotEqual(zip_uuid, zip_uuid_found)
        self.assertNotEqual(zip_archive_name, [f"{requesting_user.pk}_{zip_uuid}.zip"])
        self.assertEqual(
            zip_archive_name, [f"{requesting_user.pk}_{zip_uuid_found}.zip"]
        )
        # Clear ZIP archive in storages
        storage.delete(zip_archive_name[0])
