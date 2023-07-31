"""Management command to initialize some fake data (products, courses and course runs)"""
from django.core.management.base import BaseCommand
from django.utils import translation

import arrow

from joanie.core import enums, factories, models

OPENEDX_COURSE_RUN_URI = (
    "http://openedx.test/courses/course-v1:edx+{course:s}+{course_run:s}/course"
)


class Command(BaseCommand):
    """Create some fake data (products, courses and course runs)"""

    help = "Create some fake products, courses and course runs"

    def create_course(self, user, organization, batch_size=1, with_course_runs=False):
        """Create courses for given user and organization."""

        if batch_size == 1:
            course_runs = []
            if with_course_runs:
                course_runs = factories.CourseRunFactory.create_batch(2, is_listed=True)
            return factories.CourseFactory(
                organizations=[organization],
                users=[[user, enums.OWNER]],
                course_runs=course_runs,
            )

        courses = factories.CourseFactory.create_batch(
            batch_size, organizations=[organization], users=[[user, enums.OWNER]]
        )

        if with_course_runs:
            for course in courses:
                factories.CourseRunFactory.create_batch(
                    2, course=course, is_listed=True
                )
        return courses

    def _create_product(self, user, organization):
        """Create a single product for given user and organization."""
        course = self.create_course(user, organization)
        target_courses = self.create_course(
            user, organization, batch_size=3, with_course_runs=True
        )
        return factories.ProductFactory(
            courses=[course],
            target_courses=target_courses,
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )

    def create_product(self, user, organization, batch_size=1):
        """Create batch or products for given user and organization."""
        if batch_size == 1:
            return self._create_product(user, organization)
        return [self.create_product(user, organization) for i in range(batch_size + 1)]

    def handle(self, *args, **options):  # pylint: disable=too-many-locals
        translation.activate("en-us")

        # Create an organization
        admin_user = models.User.objects.get(username="admin")
        organization = factories.OrganizationFactory(
            title="The school of glory",
            # Give access to admin user
            users=[[admin_user, enums.OWNER]],
        )

        # First create a course product to learn how to become a botanist
        # 1/ some course runs are required to become a botanist
        bases_of_botany_run1 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="000001", course_run="BasesOfBotany_run1"
            ),
            start=arrow.utcnow().shift(days=-2).datetime,
            # Give access to admin user
            course__users=[[admin_user, enums.OWNER]],
            course__organizations=[organization],
        )
        factories.CourseRunFactory(
            title="Bases of botany",
            course=bases_of_botany_run1.course,
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="000001", course_run="BasesOfBotany_run2"
            ),
            start=arrow.utcnow().shift(days=10).datetime,
        )
        how_to_make_a_herbarium_run1 = factories.CourseRunFactory(
            title="How to make a herbarium",
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="000002", course_run="HowToMakeHerbarium_run1"
            ),
            # Give access to admin user
            course__users=[[admin_user, enums.OWNER]],
            course__organizations=[organization],
        )
        factories.CourseRunFactory(
            title="How to make a herbarium",
            course=how_to_make_a_herbarium_run1.course,
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="000002", course_run="HowToMakeHerbarium_run2"
            ),
        )
        scientific_publication_analysis_run1 = factories.CourseRunFactory(
            title="Scientific publication analysis",
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="000003", course_run="ScientificPublicationAnalysis_run1"
            ),
        )
        factories.CourseRunFactory(
            title="Scientific publication analysis",
            course=scientific_publication_analysis_run1.course,
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="000003", course_run="ScientificPublicationAnalysis_run2"
            ),
        )

        # Give courses access to admin user

        credential_courses = [
            bases_of_botany_run1.course,
            how_to_make_a_herbarium_run1.course,
            scientific_publication_analysis_run1.course,
        ]

        # Now create a course product to learn how to become a botanist and get a certificate
        # 1/ Create the credential Product linked to the botany Course
        factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            title="Become a certified botanist",
            target_courses=credential_courses,
            certificate_definition=factories.CertificateDefinitionFactory(
                title="Botanist Certification",
                name="Become a certified botanist certificate",
            ),
        )

        # We need some pagination going on, let's create few more courses and products
        self.create_course(
            admin_user, organization, batch_size=10, with_course_runs=True
        )
        self.create_product(admin_user, organization, batch_size=10)

        self.stdout.write(self.style.SUCCESS("Successfully fake data creation"))
