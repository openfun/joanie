# ruff: noqa: S311, PLR0913
"""Management command to initialize some fake data (products, courses and course runs)"""
import random

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

    def create_product_certificate_enrollment(self, user, organization):
        """Create a product certificate and it's enrollment."""
        product = self.create_product_certificate(user, organization)
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
        organization,
        product_type=enums.PRODUCT_TYPE_CERTIFICATE,
        order_status=enums.ORDER_STATE_VALIDATED,
        contract_definition=None,
    ):  # pylint: disable=too-many-arguments
        """Create a product, it's enrollment and it's order."""
        if product_type == enums.PRODUCT_TYPE_CERTIFICATE:
            product = self.create_product_certificate(user, organization)
        elif product_type == enums.PRODUCT_TYPE_CREDENTIAL:
            product = self.create_product_credential(
                user, organization, contract_definition
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

        for target_course in product.target_courses.all():
            factories.OrderTargetCourseRelationFactory(
                order=order, course=target_course
            )

        return order

    def create_product_purchased_with_certificate(
        self, user, organization, product_type, contract_definition=None
    ):
        """
        Create a product, it's enrollment and it's order.
        Also create the order's linked certificate.
        """
        order = self.create_product_purchased(
            user,
            organization,
            product_type,
            enums.ORDER_STATE_VALIDATED,
            contract_definition,
        )
        return factories.OrderCertificateFactory(order=order)

    def create_enrollment_certificate(self, user, organization):
        """create an enrollment and it's linked certificate."""
        course = self.create_course(user, organization, 1, True)
        factories.EnrollmentCertificateFactory(
            enrollment__user=user,
            enrollment__course_run=course.course_runs.first(),
            enrollment__is_active=True,
            enrollment__state=enums.ENROLLMENT_STATE_SET,
            organization=organization,
        )

    def handle(self, *args, **options):  # pylint: disable=too-many-locals
        translation.activate("en-us")

        # Create an organization
        admin_user = models.User.objects.get(username="admin")
        organization = factories.OrganizationFactory(
            title="The school of glory",
            # Give access to admin user
            users=[[admin_user, enums.OWNER]],
        )

        # Add one credit card to admin user
        payment_factories.CreditCardFactory(owner=admin_user)
        factories.AddressFactory(owner=admin_user)

        # First create a course product to learn how to become a botanist
        # 1/ some course runs are required to become a botanist
        bases_of_botany_run1 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="00001", course_run="BasesOfBotany_run1"
            ),
            # Give access to admin user
            course__users=[[admin_user, enums.OWNER]],
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
            # Give access to admin user
            course__users=[[admin_user, enums.OWNER]],
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
            admin_user,
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
            admin_user, organization, batch_size=NB_DEV_OBJECTS["product_credential"]
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully create {NB_DEV_OBJECTS['product_credential']} \
                fake PRODUCT_CREDENTIAL"
            )
        )

        self.create_product_certificate(
            admin_user, organization, batch_size=NB_DEV_OBJECTS["product_certificate"]
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully create {NB_DEV_OBJECTS['product_certificate']} \
                fake PRODUCT_CERTIFICATE"
            )
        )

        # Enrollments and orders
        self.create_product_certificate_enrollment(admin_user, organization)
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create a enrollment for a course with a PRODUCT_CERTIFICATE"
            )
        )

        # Order for a PRODUCT_CERTIFICATE
        self.create_product_purchased(
            admin_user, organization, enums.PRODUCT_TYPE_CERTIFICATE
        )
        self.stdout.write(
            self.style.SUCCESS("Successfully create a order for a PRODUCT_CERTIFICATE")
        )

        # Order for a PRODUCT_CERTIFICATE with a generated certificate
        self.create_product_purchased_with_certificate(
            admin_user, organization, enums.PRODUCT_TYPE_CERTIFICATE
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create a order for a PRODUCT_CERTIFICATE \
                with a generated certificate"
            )
        )

        # Order for a PRODUCT_CREDENTIAL with a generated certificate
        self.create_product_purchased_with_certificate(
            admin_user,
            organization,
            enums.PRODUCT_TYPE_CREDENTIAL,
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create a order for a PRODUCT_CREDENTIAL with a generated certificate"
            )
        )

        # Order for a PRODUCT_CREDENTIAL with a unsigned contract
        order = self.create_product_purchased(
            admin_user,
            organization,
            enums.PRODUCT_TYPE_CREDENTIAL,
            enums.ORDER_STATE_VALIDATED,
            factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            student_signed_on=None,
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create a order for a PRODUCT_CREDENTIAL with an unsigned contract"
            )
        )

        # Order for a PRODUCT_CREDENTIAL with a signed contract
        order = self.create_product_purchased(
            admin_user,
            organization,
            enums.PRODUCT_TYPE_CREDENTIAL,
            enums.ORDER_STATE_VALIDATED,
            factories.ContractDefinitionFactory(),
        )

        factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            student_signed_on=django_timezone.now(),
            organization_signed_on=django_timezone.now(),
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create a order for a PRODUCT_CREDENTIAL with a signed contract"
            )
        )

        # Enrollment with a certificate
        self.create_enrollment_certificate(admin_user, organization)
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully create a enrollment with a generated certificate"
            )
        )

        # Order for all existing status on PRODUCT_CREDENTIAL
        for order_status in [
            enums.ORDER_STATE_DRAFT,
            enums.ORDER_STATE_SUBMITTED,
            enums.ORDER_STATE_PENDING,
            enums.ORDER_STATE_CANCELED,
            enums.ORDER_STATE_VALIDATED,
        ]:
            self.create_product_purchased(
                admin_user,
                organization,
                enums.PRODUCT_TYPE_CREDENTIAL,
                order_status,
            )

        self.stdout.write(self.style.SUCCESS("Successfully fake data creation"))
