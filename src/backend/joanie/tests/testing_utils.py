# ruff: noqa: S311, PLR0913, PLR0915
"""Test utils module."""

import random
import sys
from importlib import reload

from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import clear_url_caches
from django.utils import timezone as django_timezone
from django.utils import translation

from beaupy import select_multiple

from joanie.core import enums, factories, models
from joanie.core.models import CourseState
from joanie.demo.defaults import NB_DEV_OBJECTS
from joanie.payment import factories as payment_factories

OPENEDX_COURSE_RUN_URI = (
    "http://openedx.test/courses/course-v1:edx+{course:s}+{course_run:s}/course"
)


def reload_urlconf():
    """
    Enforce URL configuration reload.
    Required when using override_settings for a setting present in `joanie.urls`.
    It avoids having the url routes in cache if testing different configurations
    of accessibles routes defined if settings.DEBUG is True or False. If we don't use this
    method, you will not be able to test both configuration easily within a same class test suite.
    """
    if settings.ROOT_URLCONF in sys.modules:
        # The module is already loaded, need to reload
        reload(sys.modules[settings.ROOT_URLCONF])
        clear_url_caches()
    # Otherwise, the module will be loaded normally by Django


class Demo:
    """Create some fake data (products, courses and course runs)"""

    def __init__(self, log=lambda x: None):
        """Initialize the demo object."""
        self.log = log

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
            self.log(f"Successfully create product credential on course {course.code}")
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
            self.log(f"Successfully create product certificate on course {course.code}")
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

    def add_discount(
        self,
        order,
        discount,
    ):
        """
        Add a discount (rate or amount) on an order
        """
        offering_rule = factories.OfferingRuleFactory(
            nb_seats=None,
            course_product_relation=order.product.offerings.first(),
            discount=discount,
        )
        order.offering_rules.add(offering_rule)
        order.freeze_total()

        return order

    def create_product_purchased(
        self,
        user,
        course_user,
        organization,
        product_type=enums.PRODUCT_TYPE_CERTIFICATE,
        order_status=enums.ORDER_STATE_COMPLETED,
        contract_definition=None,
        product=None,
        discount_amount=None,
        discount_rate=None,
    ):  # pylint: disable=too-many-arguments, too-many-positional-arguments
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
        if discount_amount or discount_rate:
            discount = factories.DiscountFactory(
                amount=discount_amount, rate=discount_rate
            )
            order = self.add_discount(order, discount)

        return order

    def create_product_purchased_with_certificate(
        self,
        user,
        course_user,
        organization,
        options,
        discount_amount=None,
        discount_rate=None,
    ):  # pylint: disable=too-many-arguments, too-many-positional-arguments
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
            discount_amount=discount_amount,
            discount_rate=discount_rate,
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

    def generate(self):  # pylint: disable=too-many-locals,too-many-statements
        """Generate fake data."""
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
        payment_factories.CreditCardFactory(owners=[student_user])
        factories.UserAddressFactory(owner=student_user)

        second_student_user = factories.UserFactory(
            username="second_student_user",
            email=email_user + "+second_student_user@" + email_domain,
            first_name="Étudiant 002",
        )
        payment_factories.CreditCardFactory(owners=[second_student_user])
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
        self.log(f'Successfully create "{product.title}" product')

        # We need some pagination going on, let's create few more courses and products
        self.create_course(
            organization_owner,
            organization,
            batch_size=NB_DEV_OBJECTS["course"],
            with_course_runs=True,
        )
        self.log(f"Successfully create {NB_DEV_OBJECTS['course']} fake courses")

        self.create_product_credential(
            organization_owner,
            organization,
            batch_size=NB_DEV_OBJECTS["product_credential"],
        )
        self.log(
            f"Successfully create {NB_DEV_OBJECTS['product_credential']} \
            fake PRODUCT_CREDENTIAL"
        )

        self.create_product_certificate(
            organization_owner,
            organization,
            batch_size=NB_DEV_OBJECTS["product_certificate"],
        )
        self.log(
            f"Successfully create {NB_DEV_OBJECTS['product_certificate']} \
            fake PRODUCT_CERTIFICATE"
        )

        # Enrollments and orders
        self.create_product_certificate_enrollment(
            student_user, organization_owner, organization
        )
        self.log(
            "Successfully create an enrollment for a course with a PRODUCT_CERTIFICATE"
        )

        # Order for a PRODUCT_CERTIFICATE
        self.create_product_purchased(
            student_user,
            organization_owner,
            organization,
            enums.PRODUCT_TYPE_CERTIFICATE,
        )
        self.log("Successfully create an order for a PRODUCT_CERTIFICATE")

        # Order for a PRODUCT_CERTIFICATE with a generated certificate
        self.create_product_purchased_with_certificate(
            student_user,
            organization_owner,
            organization,
            options={
                "product_type": enums.PRODUCT_TYPE_CERTIFICATE,
            },
        )
        self.log(
            "Successfully create an order for a PRODUCT_CERTIFICATE \
            with a generated certificate"
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
        self.log(
            "Successfully create an order for a PRODUCT_CREDENTIAL with a generated certificate"
        )

        # Order for a PRODUCT_CREDENTIAL with an installment payment failed
        self.create_order_with_installment_payment_failed(
            student_user,
            organization_owner,
            organization,
        )
        self.log(
            "Successfully create an order for a PRODUCT_CREDENTIAL "
            "with an installment payment failed"
        )
        # Order for PRODUCT_CERTIFICATE with discount rate of 10%
        self.create_product_purchased_with_certificate(
            student_user,
            organization_owner,
            organization,
            options={
                "product_type": enums.PRODUCT_TYPE_CERTIFICATE,
            },
            discount_rate=0.1,
        )
        self.log(
            "Successfully created an order for a PRODUCT_CERTIFICATE"
            "with a discount rate or 10%"
        )

        # Order for PRODUCT_CREDENTIAL with discount amount of 20 €
        self.create_product_purchased(
            student_user,
            organization_owner,
            organization,
            enums.PRODUCT_TYPE_CREDENTIAL,
            enums.ORDER_STATE_COMPLETED,
            factories.ContractDefinitionFactory(),
            discount_amount=20,
        )
        self.log(
            "Successfully created an order for a PRODUCT_CREDENTIAL"
            "with a discount amount or 20 €"
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
        self.log(
            "Successfully create an order for a PRODUCT_CREDENTIAL with an unsigned contract"
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

        self.log(
            f"Successfully create an order for a PRODUCT_CREDENTIAL \
            with a contract signed by a learner, organization.uuid: {organization.id}",
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

        self.log(
            f"Successfully create an order for a PRODUCT_CREDENTIAL \
        with a fully signed contract, organization.uuid: {organization.id}",
        )

        # Enrollment with a certificate
        self.create_enrollment_certificate(
            student_user, organization_owner, organization
        )
        self.log("Successfully create an enrollment with a generated certificate")

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
        self.log("Successfully set organization owner access for each organization")

        self.log("Successfully fake data creation")

        for order in models.Order.objects.all():
            try:
                order.generate_schedule()
            except ValidationError:
                continue

            if order.state == enums.ORDER_STATE_COMPLETED:
                for installment in order.payment_schedule:
                    order.set_installment_paid(installment["id"])

            if order.state == enums.ORDER_STATE_PENDING_PAYMENT:
                order.set_installment_paid(order.payment_schedule[0]["id"])

            if order.state == enums.ORDER_STATE_FAILED_PAYMENT:
                order.set_installment_refused(order.payment_schedule[0]["id"])

            if order.state == enums.ORDER_STATE_CANCELED:
                order.cancel_remaining_installments()

            if order.state == enums.ORDER_STATE_REFUNDING:
                order.set_installment_paid(order.payment_schedule[0]["id"])
                order.cancel_remaining_installments()

            if order.state == enums.ORDER_STATE_REFUNDED:
                order.set_installment_paid(order.payment_schedule[0]["id"])
                order.set_installment_refunded(order.payment_schedule[0]["id"])
                order.cancel_remaining_installments()

    def generate_simple(self):  # pylint: disable=too-many-locals,too-many-statements
        """Generate simple fake data."""
        translation.activate("en-us")

        # Create an organization
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
            users=[[organization_owner, enums.OWNER]],
        )

        # Add one credit card to student user
        student_user = factories.UserFactory(
            username="student_user",
            email=email_user + "+student_user@" + email_domain,
            first_name="Étudiant",
        )
        payment_factories.CreditCardFactory(owners=[student_user])
        factories.UserAddressFactory(owner=student_user)

        second_student_user = factories.UserFactory(
            username="second_student_user",
            email=email_user + "+second_student_user@" + email_domain,
            first_name="Étudiant 002",
        )
        payment_factories.CreditCardFactory(owners=[second_student_user])
        factories.UserAddressFactory(owner=second_student_user)
        discount = factories.DiscountFactory(
            amount=10,
            rate=None,
        )

        item_options = [
            "Certificate product",
            "Certificate product with discount",
            "Credential product",
            "Credential product with discount",
        ]
        items = select_multiple(item_options)

        if "Certificate product" in items:
            course = factories.CourseFactory(
                code="00000",
                title="Course for certificate",
                users=[[organization_owner, enums.OWNER]],
                organizations=[organization],
            )
            self.log(f'Successfully created "{course.title}" course')
            self.log("")

            course_run_certificate = factories.CourseRunFactory(
                title="Course run certificate",
                resource_link=OPENEDX_COURSE_RUN_URI.format(
                    course="00000", course_run="CourseRunCertificate_run1"
                ),
                course=course,
                languages=self.get_random_languages(),
                state=CourseState.ONGOING_OPEN,
                is_listed=True,
            )
            self.log(
                f'Successfully created "{course_run_certificate.title}" course run'
            )
            self.log("")

            certificate_product = factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                title="Certificate Product",
                courses=[course_run_certificate.course],
                target_courses=[],
                certificate_definition=factories.CertificateDefinitionFactory(
                    title="Certification",
                    name="Become a certified learner certificate",
                ),
                price=100,
            )
            self.log(f'Successfully created "{certificate_product.title}" product')
            self.log("")

            course_run_certificate.save()

        if "Certificate product with discount" in items:
            course = factories.CourseFactory(
                code="00001",
                title="Course for certificate with discount",
                users=[[organization_owner, enums.OWNER]],
                organizations=[organization],
            )
            self.log(f'Successfully created "{course.title}" course')
            self.log("")

            course_run_certificate_discount = factories.CourseRunFactory(
                title="Course run certificate discount",
                resource_link=OPENEDX_COURSE_RUN_URI.format(
                    course="00001", course_run="CourseRunCertificate_run1"
                ),
                course=course,
                languages=self.get_random_languages(),
                state=CourseState.ONGOING_OPEN,
                is_listed=True,
            )
            self.log(
                f'Successfully created "{course_run_certificate_discount.title}" course run'
            )
            self.log("")

            certificate_product_discount = factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                title="Certificate Product with discount",
                courses=[course_run_certificate_discount.course],
                target_courses=[],
                certificate_definition=factories.CertificateDefinitionFactory(
                    title="Certification discount",
                    name="Become a discounted learner certificate",
                ),
                price=100,
            )
            self.log(
                f'Successfully created "{certificate_product_discount.title}" product'
            )
            self.log("")

            certificate_discount_offering = models.CourseProductRelation.objects.get(
                course=certificate_product_discount.courses.first(),
                product=certificate_product_discount,
            )
            self.log(
                f'Successfully created "{certificate_discount_offering}" '
                "offering (course product relation)"
            )
            self.log("")

            factories.OfferingRuleFactory(
                course_product_relation=certificate_discount_offering,
                discount=discount,
            )
            self.log("Successfully created offering rule")
            self.log("")

            course_run_certificate_discount.save()

        if "Credential product" in items:
            course = factories.CourseFactory(
                code="00002",
                title="Course for credential",
                users=[[organization_owner, enums.OWNER]],
                organizations=[organization],
            )
            self.log(f'Successfully created "{course.title}" course')
            self.log("")

            course_run_credential = factories.CourseRunFactory(
                title="Course run credential",
                resource_link=OPENEDX_COURSE_RUN_URI.format(
                    course="00002", course_run="CourseRunCredential_run1"
                ),
                course=course,
                languages=self.get_random_languages(),
                state=CourseState.ONGOING_OPEN,
                is_listed=False,
            )
            self.log(f'Successfully created "{course_run_credential.title}" course run')
            self.log("")

            credential_product = factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CREDENTIAL,
                title="Credential Product",
                courses=[course_run_credential.course],
                target_courses=[
                    course_run_credential.course,
                ],
                price=100,
            )
            self.log(f'Successfully created "{credential_product.title}" product')
            self.log("")

            course_run_credential.save()

        if "Credential product with discount" in items:
            course = factories.CourseFactory(
                code="00003",
                title="Course for credential with discount",
                users=[[organization_owner, enums.OWNER]],
                organizations=[organization],
            )
            self.log(f'Successfully created "{course.title}" course')
            self.log("")

            course_run_credential_discount = factories.CourseRunFactory(
                title="Course run credential discount",
                resource_link=OPENEDX_COURSE_RUN_URI.format(
                    course="00003", course_run="CourseRunCredential_run1"
                ),
                course=course,
                languages=self.get_random_languages(),
                state=CourseState.ONGOING_OPEN,
                is_listed=True,
            )
            self.log(
                f'Successfully created "{course_run_credential_discount.title}" course run'
            )
            self.log("")

            credential_product_discount = factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CREDENTIAL,
                title="Credential Product with discount",
                courses=[course_run_credential_discount.course],
                target_courses=[
                    factories.CourseFactory(
                        organizations=[organization],
                        title="Target Course for credential product discount",
                        course_runs=factories.CourseRunFactory.create_batch(
                            1, course__code="cred_disc"
                        ),
                        code="00003",
                    )
                ],
                price=100,
            )
            self.log(
                f'Successfully created "{credential_product_discount.title}" product'
            )
            self.log("")

            credential_discount_offering = models.CourseProductRelation.objects.get(
                course=credential_product_discount.courses.first(),
                product=credential_product_discount,
            )
            self.log(
                f'Successfully created "{credential_discount_offering}" '
                "offering (course product relation)"
            )
            self.log("")

            factories.OfferingRuleFactory(
                course_product_relation=credential_discount_offering,
                discount=discount,
            )
            self.log("Successfully created offering rule")
            self.log("")

            course_run_credential_discount.save()
