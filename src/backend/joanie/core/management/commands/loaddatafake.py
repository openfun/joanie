from django.core.management.base import BaseCommand
from django.utils import translation

from joanie.core import factories
from joanie.core import enums


class Command(BaseCommand):
    help = 'create some fake products, courses and course runs'

    def handle(self, *args, **options):
        translation.activate('en')
        # First create a course product to learn how to become a good druid
        # 1/ some course runs are required to became a good druid
        OPENEDX_COURSE_RUN_URI = "http://openedx.test/courses/course-v1:edx+%s/course"
        bases_of_botany_session1 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI % '000001+BasesOfBotany_Session1',
        )
        bases_of_botany_session2 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI % '000001+BasesOfBotany_Session2',
        )
        bases_of_druidism_session1 = factories.CourseRunFactory(
            title="Bases of druidism",
            resource_link=OPENEDX_COURSE_RUN_URI % '000002+BasesOfDruidism_Session1',
        )
        bases_of_druidism_session2 = factories.CourseRunFactory(
            title="Bases of druidism",
            resource_link=OPENEDX_COURSE_RUN_URI % '000002+BasesOfDruidism_Session2',
        )
        diy_magic_potion_session1 = factories.CourseRunFactory(
            title="How to cook a magic potion",
            resource_link=OPENEDX_COURSE_RUN_URI % '000003+DIYMagicPotion_Session1',
        )
        diy_magic_potion_session2 = factories.CourseRunFactory(
            title="How to cook a magic potion",
            resource_link=OPENEDX_COURSE_RUN_URI % '000003+DIYMagicPotion_Session2',
        )
        # 2/ Create the enrollment Product
        become_druid_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_ENROLLMENT,
            title="Become druid",
        )
        # 3/ Create the Course of organization "the Druid School"
        druid_school = factories.OrganizationFactory(title="the Druid School")
        druid_course = factories.CourseFactory(
            title="Druid course",
            organization=druid_school,
        )
        # 4/ now link the Product to the Druid Course
        course_product_druid = factories.CourseProductFactory(
            course=druid_course,
            product=become_druid_product,
        )
        # 5/ add all course runs available for this course product
        course_product_druid.course_runs.add(bases_of_botany_session1)
        course_product_druid.course_runs.add(bases_of_druidism_session1)
        course_product_druid.course_runs.add(diy_magic_potion_session1)

        course_product_druid.course_runs.add(bases_of_botany_session2)
        course_product_druid.course_runs.add(bases_of_druidism_session2)
        course_product_druid.course_runs.add(diy_magic_potion_session2)

        # 6/ now define position of each course runs to complete the course
        # first to do
        factories.ProductCourseRunPositionFactory(
            course_run=bases_of_botany_session1,
            position=1,
            course_product=course_product_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=bases_of_botany_session2,
            position=1,
            course_product=course_product_druid,
        )
        # second to do
        factories.ProductCourseRunPositionFactory(
            course_run=bases_of_druidism_session1,
            position=2,
            course_product=course_product_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=bases_of_druidism_session2,
            position=2,
            course_product=course_product_druid,
        )
        # third to do
        factories.ProductCourseRunPositionFactory(
            course_run=diy_magic_potion_session1,
            position=3,
            course_product=course_product_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=diy_magic_potion_session2,
            position=3,
            course_product=course_product_druid,
        )

        # Now create a course product to learn how to become a good druid and get a certificate
        # 1/ Create the credential Product
        become_certified_druid = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            title="Become a certified druid",
        )
        # 2/ now link the Product to the Druid Course
        course_product_certified_druid = factories.CourseProductFactory(
            course=druid_course,
            product=become_certified_druid,
            certificate_definition=factories.CertificateDefinitionFactory(
                title="Druid Certification",
            ),
        )
        # 3/ add all course runs available for this course product
        course_product_certified_druid.course_runs.add(bases_of_botany_session1)
        course_product_certified_druid.course_runs.add(bases_of_druidism_session1)
        course_product_certified_druid.course_runs.add(diy_magic_potion_session1)

        course_product_certified_druid.course_runs.add(bases_of_botany_session2)
        course_product_certified_druid.course_runs.add(bases_of_druidism_session2)
        course_product_certified_druid.course_runs.add(diy_magic_potion_session2)

        # 4/ now define position of each course runs to complete the course
        # first to do
        factories.ProductCourseRunPositionFactory(
            course_run=bases_of_botany_session1,
            position=1,
            course_product=course_product_certified_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=bases_of_botany_session2,
            position=1,
            course_product=course_product_certified_druid,
        )
        # second to do
        factories.ProductCourseRunPositionFactory(
            course_run=bases_of_druidism_session1,
            position=2,
            course_product=course_product_certified_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=bases_of_druidism_session2,
            position=2,
            course_product=course_product_certified_druid,
        )
        # third to do
        factories.ProductCourseRunPositionFactory(
            course_run=diy_magic_potion_session1,
            position=3,
            course_product=course_product_certified_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=diy_magic_potion_session2,
            position=3,
            course_product=course_product_certified_druid,
        )

        # Now create a course product to learn how hunt boar
        # 1/ Create course runs needed to course
        track_boar_session = factories.CourseRunFactory(title="How to track a wild boar")
        archery_session = factories.CourseRunFactory(title="How to shoot archery")

        # 2/ Create the enrollment Product
        become_boar_hunter_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_ENROLLMENT,
            title="Become a wild boar hunter",
        )
        # 3/ Create the Course of organization "the Druid School"
        hunting_course = factories.CourseFactory(
            title="Hunting course",
            organization=factories.OrganizationFactory(title="the hunting and fishing School"),
        )
        # 4/ now link the Product to the hunting course
        course_product_hunting = factories.CourseProductFactory(
            course=hunting_course,
            product=become_boar_hunter_product,
        )
        # 5/ add all course runs available for this course product
        course_product_hunting.course_runs.add(track_boar_session)
        course_product_hunting.course_runs.add(archery_session)

        # 6/ now define position of each course runs to complete the course
        # first to do
        factories.ProductCourseRunPositionFactory(
            course_run=track_boar_session,
            position=1,
            course_product=course_product_hunting,
        )
        # second to do
        factories.ProductCourseRunPositionFactory(
            course_run=archery_session,
            position=2,
            course_product=course_product_hunting,
        )

        self.stdout.write(self.style.SUCCESS('Successfully fun data creation'))
