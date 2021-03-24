"""Management command to initialize some fake data (products, courses and course runs)"""
from django.core.management.base import BaseCommand
from django.utils import translation

import arrow

from joanie.core import enums, factories

OPENEDX_COURSE_RUN_URI = "http://openedx.test/courses/course-v1:edx+%s/course"


class Command(BaseCommand):
    """Create some fake data (products, courses and course runs)"""

    help = "Create some fake products, courses and course runs"

    def handle(self, *args, **options):  # pylint: disable=too-many-locals
        translation.activate("en-us")
        # First create a course product to learn how to become a botanist
        # 1/ some course runs are required to became a botanist
        bases_of_botany_run1 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI % "000001+BasesOfBotany_run1",
            start=arrow.utcnow().shift(days=-2).datetime,
        )
        bases_of_botany_run2 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI % "000001+BasesOfBotany_run2",
            start=arrow.utcnow().shift(days=10).datetime,
        )
        how_to_make_a_herbarium_run1 = factories.CourseRunFactory(
            title="How to make a herbarium",
            resource_link=OPENEDX_COURSE_RUN_URI % "000002+HowToMakeHerbarium_run1",
        )
        how_to_make_a_herbarium_run2 = factories.CourseRunFactory(
            title="How to make a herbarium",
            resource_link=OPENEDX_COURSE_RUN_URI % "000002+HowToMakeHerbarium_run2",
        )
        scientific_publication_analysis_run1 = factories.CourseRunFactory(
            title="Scientific publication analysis",
            resource_link=OPENEDX_COURSE_RUN_URI
            % "000003+ScientificPublicationAnalysis_run1",
        )
        scientific_publication_analysis_run2 = factories.CourseRunFactory(
            title="Scientific publication analysis",
            resource_link=OPENEDX_COURSE_RUN_URI
            % "000003+ScientificPublicationAnalysis_run2",
        )
        botanist_course_runs = [
            bases_of_botany_run1,
            bases_of_botany_run2,
            how_to_make_a_herbarium_run1,
            how_to_make_a_herbarium_run2,
            scientific_publication_analysis_run1,
            scientific_publication_analysis_run2,
        ]
        botanist_course_runs_position_todo = [
            (1, bases_of_botany_run1),
            (1, bases_of_botany_run2),
            (2, how_to_make_a_herbarium_run1),
            (2, how_to_make_a_herbarium_run2),
            (3, scientific_publication_analysis_run1),
            (3, scientific_publication_analysis_run2),
        ]

        # 2/ Create the Course of organization "the Botany School"
        botanist_course = factories.CourseFactory(
            title="botany course",
            organization=factories.OrganizationFactory(title="the Botany School"),
        )
        # 3/ Create the enrollment product for the botany course
        become_botanist_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_ENROLLMENT,
            title="Become botanist",
            course=botanist_course,
            price=100,
        )
        # 4/ add all course runs available for this course product
        become_botanist_product.course_runs.set(botanist_course_runs)

        # 5/ now define position of each course runs to complete the course
        for position, course_run in botanist_course_runs_position_todo:
            factories.ProductCourseRunPositionFactory(
                product=become_botanist_product,
                position=position,
                course_run=course_run,
            )

        # Now create a course product to learn how to become a botanist and get a certificate
        # 1/ Create the credential Product linked to the botany Course
        become_certified_botanist_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            title="Become a certified botanist",
            course=botanist_course,
            certificate_definition=factories.CertificateDefinitionFactory(
                title="Botanist Certification",
            ),
        )
        # 2/ add all course runs available for this course product
        become_certified_botanist_product.course_runs.set(botanist_course_runs)

        # 3/ now define position of each course runs to complete the course
        for position, course_run in botanist_course_runs_position_todo:
            factories.ProductCourseRunPositionFactory(
                product=become_certified_botanist_product,
                position=position,
                course_run=course_run,
            )

        self.stdout.write(self.style.SUCCESS("Successfully fake data creation"))
