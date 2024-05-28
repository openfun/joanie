# ruff: noqa: S311, PLR0913, PLR0915
"""Management command to initialize some fake data (products, courses and course runs)"""

import random

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone as django_timezone
from django.utils import translation

from joanie.core import enums, factories, models
from joanie.core.models import CourseState
from joanie.demo.defaults import NB_DEV_OBJECTS
from joanie.payment import factories as payment_factories

OPENEDX_COURSE_RUN_URI = (
    "http://openedx.test/courses/course-v1:edx+{course:s}+{course_run:s}/course"
)


class Command(BaseCommand):
    """Create some fake data (products, courses and course runs)"""

    help = "Create some fake credential products, courses and course runs"

    def get_random_languages(self):
        """
        Return a set of random languages.
        global_settings.languages is not consistent between django version so we do
        want to use ALL_LANGUAGES to set course run languages to prevent synchronization
        issues between Joanie & Richie.
        """
        return random.sample(["de", "en", "fr", "pt"], random.randint(1, 4))

    def create_course(self, user, organization, batch_size=1, with_course_runs=False):
        """Create courses for given user and organization."""

        if batch_size == 1:
            course = factories.CourseFactory(
                organizations=[organization],
                users=[[user, enums.OWNER]],
            )
            if with_course_runs:
                factories.CourseRunFactory.create_batch(
                    2,
                    is_listed=True,
                    state=CourseState.ONGOING_OPEN,
                    languages=self.get_random_languages(),
                    course=course,
                )

            return course

        courses = factories.CourseFactory.create_batch(
            batch_size, organizations=[organization], users=[[user, enums.OWNER]]
        )

        if with_course_runs:
            for course in courses:
                factories.CourseRunFactory.create_batch(
                    2,
                    course=course,
                    is_listed=True,
                    state=CourseState.ONGOING_OPEN,
                    languages=self.get_random_languages(),
                )
        return courses

    def create_product_credential(
        self, user, organization, contract_definition=None, batch_size=1
    ):
        """Create batch or products for given user and organization."""
        if batch_size == 1:
            course = factories.CourseFactory(
                organizations=[organization],
                users=[[user, enums.OWNER]],
            )
            product = factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CREDENTIAL,
                courses=[course],
                contract_definition=contract_definition,
            )
            target_course_list = factories.CourseFactory.create_batch(
                2,
                organizations=[organization],
                users=[[user, enums.OWNER]],
            )

            for target_course in target_course_list:
                factories.CourseRunFactory(
                    course=target_course,
                    is_listed=True,
                    state=CourseState.ONGOING_OPEN,
                    languages=self.get_random_languages(),
                    resource_link=OPENEDX_COURSE_RUN_URI.format(
                        course=target_course.code, course_run="{course.title}_run1"
                    ),
                )
                factories.CourseRunFactory(
                    course=target_course,
                    is_listed=True,
                    state=CourseState.ONGOING_OPEN,
                    languages=self.get_random_languages(),
                    resource_link=OPENEDX_COURSE_RUN_URI.format(
                        course=target_course.code, course_run="{course.title}_run2"
                    ),
                )
                factories.ProductTargetCourseRelationFactory(
                    course=target_course, product=product
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully create product credential on course {course.code}"
                )
            )
            return product
        return [
            self.create_product_credential(user, organization)
            for i in range(batch_size)
        ]

    def create_product_certificate(self, user, organization, batch_size=1):
        """Create batch or products certificate for given user and organization."""
        if batch_size == 1:
            course = factories.CourseFactory(
                organizations=[organization],
                users=[[user, enums.OWNER]],
            )
            factories.CourseRunFactory(
                course=course,
                is_listed=True,
                state=CourseState.ONGOING_OPEN,
                languages=self.get_random_languages(),
                resource_link=OPENEDX_COURSE_RUN_URI.format(
                    course=course.code, course_run="{course.title}_run1"
                ),
            )
            factories.CourseRunFactory(
                course=course,
                is_listed=True,
                state=CourseState.ONGOING_OPEN,
                languages=self.get_random_languages(),
                resource_link=OPENEDX_COURSE_RUN_URI.format(
                    course=course.code, course_run="{course.title}_run2"
                ),
            )
            product = factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                courses=[course],
                contract_definition=None,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully create product certificate on course {course.code}"
                )
            )
            return product
        return [
            self.create_product_certificate(user, organization)
            for i in range(batch_size)
        ]

    def create_product_certificate_enrollment(self, user, course_user, organization):
        """Create a product certificate and it's enrollment."""
        product = self.create_product_certificate(course_user, organization)
        course = product.courses.first()
        return factories.EnrollmentFactory(
            user=user,
            course_run=course.course_runs.first(),
            is_active=True,
            state=enums.ENROLLMENT_STATE_SET,
        )

    def create_product_purchased(
        self,
        user,
        course_user,
        organization,
        product_type=enums.PRODUCT_TYPE_CERTIFICATE,
        order_status=enums.ORDER_STATE_COMPLETED,
        contract_definition=None,
        product=None,
    ):  # pylint: disable=too-many-arguments
        """Create a product, it's enrollment and it's order."""
        if not product:
            if product_type == enums.PRODUCT_TYPE_CERTIFICATE:
                product = self.create_product_certificate(course_user, organization)
            elif product_type == enums.PRODUCT_TYPE_CREDENTIAL:
                product = self.create_product_credential(
                    course_user, organization, contract_definition
                )
            else:
                raise ValueError(f"Given product_type ({product_type}) is not allowed.")

        course = product.courses.first()

        order = factories.OrderFactory(
            course=None if product_type == enums.PRODUCT_TYPE_CERTIFICATE else course,
            enrollment=factories.EnrollmentFactory(
                user=user,
                course_run=course.course_runs.first(),
                is_active=True,
                state=enums.ENROLLMENT_STATE_SET,
            )
            if product_type == enums.PRODUCT_TYPE_CERTIFICATE
            else None,
            owner=user,
            product=product,
            state=order_status,
        )

        return order

    def create_product_purchased_with_certificate(
        self, user, course_user, organization, options
    ):
        """
        Create a product, it's enrollment and it's order.
        Also create the order's linked certificate.
        """
        order = self.create_product_purchased(
            user,
            course_user,
            organization,
            options["product_type"],
            enums.ORDER_STATE_COMPLETED,
            options["contract_definition"]
            if "contract_definition" in options
            else None,
        )
        return factories.OrderCertificateFactory(order=order)

    def create_order_with_installment_payment_failed(
        self, user, course_user, organization
    ):
        """
        Create an order with an installment payment failed.
        """

        order = self.create_product_purchased(
            user,
            course_user,
            organization,
            enums.PRODUCT_TYPE_CREDENTIAL,
            enums.ORDER_STATE_PENDING,
            factories.ContractDefinitionFactory(),
        )

        factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            submitted_for_signature_on=django_timezone.now(),
            student_signed_on=django_timezone.now(),
        )

        payment_factories.InvoiceFactory(
            order=order, recipient_address__owner=order.owner, total=order.total
        )

        order.generate_schedule()
        installment = order.payment_schedule[0]
        order.set_installment_refused(installment["id"])
        order.save()

    def create_enrollment_certificate(self, user, course_user, organization):
        """create an enrollment and it's linked certificate."""
        course = self.create_course(course_user, organization, 1, True)
        factories.EnrollmentCertificateFactory(
            enrollment__user=user,
            enrollment__course_run=course.course_runs.first(),
            enrollment__is_active=True,
            enrollment__state=enums.ENROLLMENT_STATE_SET,
            organization=organization,
        )

    def handle(self, *args, **options):  # pylint: disable=too-many-locals,too-many-statements
        translation.activate("en-us")

        # Create an organization
        other_owners = factories.UserFactory.create_batch(
            5,
            first_name="Other",
            last_name="Owner",
        )
        email = settings.DEVELOPER_EMAIL
        email_user, email_domain = email.split("@")

        organization_owner = factories.UserFactory(
            username="organization_owner",
            email=email_user + "+organization_owner@" + email_domain,
            first_name="Orga",
            last_name="Owner",
        )
        organization = factories.OrganizationFactory(
            title="The school of glory",
            # Give access to admin user
            users=[[organization_owner, enums.OWNER]]
            + [[owner, enums.OWNER] for owner in other_owners],
        )

        # Add one credit card to student user
        student_user = factories.UserFactory(
            username="student_user",
            email=email_user + "+student_user@" + email_domain,
            first_name="Étudiant",
        )
        payment_factories.CreditCardFactory(owner=student_user)
        factories.UserAddressFactory(owner=student_user)

        second_student_user = factories.UserFactory(
            username="second_student_user",
            email=email_user + "+second_student_user@" + email_domain,
            first_name="Étudiant 002",
        )
        payment_factories.CreditCardFactory(owner=second_student_user)
        factories.UserAddressFactory(owner=second_student_user)

        # First create a course product to learn how to become a botanist
        # 1/ some course runs are required to become a botanist
        bases_of_botany_run1 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="00001", course_run="BasesOfBotany_run1"
            ),
            # Give access to organization owner user
            course__users=[[organization_owner, enums.OWNER]],
            course__organizations=[organization],
            languages=self.get_random_languages(),
            state=CourseState.ONGOING_OPEN,
        )
        factories.CourseRunFactory(
            title="Bases of botany",
            course=bases_of_botany_run1.course,
            languages=self.get_random_languages(),
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="00001", course_run="BasesOfBotany_run2"
            ),
            state=CourseState.ONGOING_OPEN,
        )
        how_to_make_a_herbarium_run1 = factories.CourseRunFactory(
            title="How to make a herbarium",
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="00002", course_run="HowToMakeHerbarium_run1"
            ),
            # Give access to organization owner user
            course__users=[[organization_owner, enums.OWNER]],
            course__organizations=[organization],
            languages=self.get_random_languages(),
            state=CourseState.ONGOING_OPEN,
        )
        factories.CourseRunFactory(
            title="How to make a herbarium",
            course=how_to_make_a_herbarium_run1.course,
            languages=self.get_random_languages(),
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="00002", course_run="HowToMakeHerbarium_run2"
            ),
            state=CourseState.ONGOING_OPEN,
        )
        scientific_publication_analysis_run1 = factories.CourseRunFactory(
            title="Scientific publication analysis",
            languages=self.get_random_languages(),
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="00003", course_run="ScientificPublicationAnalysis_run1"
            ),
            state=CourseState.ONGOING_OPEN,
        )
        factories.CourseRunFactory(
            title="Scientific publication analysis",
            course=scientific_publication_analysis_run1.course,
            languages=self.get_random_languages(),
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="00003", course_run="ScientificPublicationAnalysis_run2"
            ),
            state=CourseState.ONGOING_OPEN,
        )

        # Give courses access to admin user

        credential_courses = [
            bases_of_botany_run1.course,
            how_to_make_a_herbarium_run1.course,
            scientific_publication_analysis_run1.course,
        ]

        # Now create a course product to learn how to become a botanist and get a certificate
        # 1/ Create the credential Product linked to the botany Course
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            # organization=[organization],
            title="Become a certified botanist",
            courses=[factories.CourseFactory(organizations=[organization])],
            target_courses=credential_courses,
            certificate_definition=factories.CertificateDefinitionFactory(
                title="Botanist Certification",
                name="Become a certified botanist certificate",
            ),
        )
        self.stdout.write(
            self.style.SUCCESS(f'Successfully create "{product.title}" product')
        )

        # We need some pagination going on, let's create few more courses and products
        self.create_course(
            organization_owner,
            organization,
            batch_size=NB_DEV_OBJECTS["course"],
            with_course_runs=True,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully create {NB_DEV_OBJECTS['course']} fake courses"
            )
        )

        self.create_product_credential(
            organization_owner,
            organization,
            batch_size=NB_DEV_OBJECTS["product_credential"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully create {NB_DEV_OBJECTS['product_credential']} \
                fake PRODUCT_CREDENTIAL"
            )
        )

        self.create_product_certificate(
            organization_owner,
            organization,
            batch_size=NB_DEV_OBJECTS["product_certificate"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully create {NB_DEV_OBJECTS['product_certificate']} \
                fake PRODUCT_CERTIFICATE"
            )
        )

        # Enrollments and orders
        self.create_product_certificate_enrollment(
            student_user, organization_owner, organization
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create an enrollment for a course with a PRODUCT_CERTIFICATE"
            )
        )

        # Order for a PRODUCT_CERTIFICATE
        self.create_product_purchased(
            student_user,
            organization_owner,
            organization,
            enums.PRODUCT_TYPE_CERTIFICATE,
        )
        self.stdout.write(
            self.style.SUCCESS("Successfully create an order for a PRODUCT_CERTIFICATE")
        )

        # Order for a PRODUCT_CERTIFICATE with a generated certificate
        self.create_product_purchased_with_certificate(
            student_user,
            organization_owner,
            organization,
            options={
                "product_type": enums.PRODUCT_TYPE_CERTIFICATE,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create an order for a PRODUCT_CERTIFICATE \
                with a generated certificate"
            )
        )

        # Order for a PRODUCT_CREDENTIAL with a generated certificate
        self.create_product_purchased_with_certificate(
            student_user,
            organization_owner,
            organization,
            options={
                "product_type": enums.PRODUCT_TYPE_CREDENTIAL,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create an order for a PRODUCT_CREDENTIAL with a generated certificate"
            )
        )

        # Order for a PRODUCT_CREDENTIAL with an installment payment failed
        self.create_order_with_installment_payment_failed(
            student_user,
            organization_owner,
            organization,
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create an order for a PRODUCT_CREDENTIAL "
                "with an installment payment failed"
            )
        )

        # Order for a PRODUCT_CREDENTIAL with a unsigned contract
        order = self.create_product_purchased(
            student_user,
            organization_owner,
            organization,
            enums.PRODUCT_TYPE_CREDENTIAL,
            enums.ORDER_STATE_COMPLETED,
            factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            student_signed_on=None,
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create an order for a PRODUCT_CREDENTIAL with an unsigned contract"
            )
        )

        # Order for a PRODUCT_CREDENTIAL with a learner signed contract
        learner_signed_order = self.create_product_purchased(
            student_user,
            organization_owner,
            organization,
            enums.PRODUCT_TYPE_CREDENTIAL,
            enums.ORDER_STATE_COMPLETED,
            factories.ContractDefinitionFactory(),
        )

        factories.ContractFactory(
            order=learner_signed_order,
            definition=learner_signed_order.product.contract_definition,
            submitted_for_signature_on=django_timezone.now(),
            student_signed_on=django_timezone.now(),
        )

        # create a second purchase with a learner signed contract for the same PRODUCT_CREDENTIAL
        order = self.create_product_purchased(
            second_student_user,
            organization_owner,
            organization,
            enums.PRODUCT_TYPE_CREDENTIAL,
            enums.ORDER_STATE_COMPLETED,
            factories.ContractDefinitionFactory(),
            product=learner_signed_order.product,
        )
        factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            submitted_for_signature_on=django_timezone.now(),
            student_signed_on=django_timezone.now(),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully create an order for a PRODUCT_CREDENTIAL \
                with a contract signed by a learner, organization.uuid: {organization.id}",
            )
        )

        # Order for a PRODUCT_CREDENTIAL with a fully signed contract
        order = self.create_product_purchased(
            student_user,
            organization_owner,
            organization,
            enums.PRODUCT_TYPE_CREDENTIAL,
            enums.ORDER_STATE_COMPLETED,
            factories.ContractDefinitionFactory(),
        )

        factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            student_signed_on=django_timezone.now(),
            organization_signed_on=django_timezone.now(),
            organization_signatory=organization_owner,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully create an order for a PRODUCT_CREDENTIAL \
                with a fully signed contract, organization.uuid: {organization.id}",
            )
        )

        # Enrollment with a certificate
        self.create_enrollment_certificate(
            student_user, organization_owner, organization
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create an enrollment with a generated certificate"
            )
        )

        # Order for all existing status on PRODUCT_CREDENTIAL
        for order_status, _ in enums.ORDER_STATE_CHOICES:
            self.create_product_purchased(
                student_user,
                organization_owner,
                organization,
                enums.PRODUCT_TYPE_CREDENTIAL,
                order_status,
            )

        # Set organization owner for each organization
        for organization in models.Organization.objects.all():
            models.OrganizationAccess.objects.get_or_create(
                user=organization_owner,
                organization=organization,
                role=enums.OWNER,
            )
            for other_owner in other_owners:
                models.OrganizationAccess.objects.get_or_create(
                    user=other_owner,
                    organization=organization,
                    role=enums.OWNER,
                )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully set organization owner access for each organization"
            )
        )

        self.stdout.write(self.style.SUCCESS("Successfully fake data creation"))
