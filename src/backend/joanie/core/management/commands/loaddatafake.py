"""Management command to initialize some fake data (products, courses and course runs)"""
from django.core.management.base import BaseCommand
from django.utils import translation

import arrow

from joanie.core import enums, factories

OPENEDX_COURSE_RUN_URI = (
    "http://openedx.test/courses/course-v1:edx+{course:s}+{course_run:s}/course"
)


class Command(BaseCommand):
    """Create some fake data (products, courses and course runs)"""

    help = "Create some fake products, courses and course runs"

    def handle(self, *args, **options):  # pylint: disable=too-many-locals
        translation.activate("en-us")
        # First create a course product to learn how to become a botanist
        # 1/ some course runs are required to become a botanist
        bases_of_botany_run1 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI.format(
                course="000001", course_run="BasesOfBotany_run1"
            ),
            start=arrow.utcnow().shift(days=-2).datetime,
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
            certificate=factories.CertificateFactory(
                title="Botanist Certification",
            ),
        )

        self.stdout.write(self.style.SUCCESS("Successfully fake data creation"))
