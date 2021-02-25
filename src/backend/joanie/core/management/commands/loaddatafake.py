from django.core.management.base import BaseCommand

from joanie.core import factories
from joanie.core import enums


class Command(BaseCommand):
    help = 'create some fake products, courses and course runs'

    def handle(self, *args, **options):
        # TODO: set language in fr or use english label
        factories.CourseRunFactory(title="Comment assommer un romain")
        factories.CourseRunFactory(title="Comment reconnaître un romain")
        factories.CourseRunFactory(title="Fabriquer une canne à pêche")
        factories.CourseRunFactory(title="Comment soulever une charge")
        hunt_boar = factories.CourseRunFactory(title="Apprendre à pister un sanglier")
        archery = factories.CourseRunFactory(title="Apprendre à tirer à l'arc")
        basics_of_botany = factories.CourseRunFactory(title="Le BABA de la botanique")
        basics_druidic = factories.CourseRunFactory(title="Le BABA druidique")
        # TODO: add same course run but with other date
        magic_potion = factories.CourseRunFactory(
            title="Comment faire une potion magique",
        )

        # initialize some product
        druid_credential_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            name="devenir-druide-certifie",
            title="Devenir druide certifié",
        )
        become_druid_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_ENROLLMENT,
            name="devenir-druide",
            title="Devenir druide",
        )
        factories.ProductFactory(
            type=enums.PRODUCT_TYPE_ENROLLMENT,
            name="devenir-lanceur-menhir",
            title="Devenir lanceur de menhir",
        )
        become_hunter_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_ENROLLMENT,
            name="devenir-chasseur-sanglier",
            title="Devenir chasseur de sanglier",
        )

        # initialize some organizations
        orga_druid = factories.OrganizationFactory(title="École des druides")
        orga_hunting_fishing = factories.OrganizationFactory(title="École chasse et pêche")
        orga_bodyb = factories.OrganizationFactory(title="École bodybuilding")

        # initilize some courses
        druid_course = factories.CourseFactory(
            title="Formation druide",
            organization=orga_druid,
        )
        factories.CourseFactory(
            title="Formation assistant druide",
            organization=orga_druid,
        )
        hunting_course = factories.CourseFactory(
            title="Formation chasseur sanglier",
            organization=orga_hunting_fishing,
        )
        factories.CourseFactory(
            title="Formation pêcheur",
            organization=orga_hunting_fishing,
        )
        factories.CourseFactory(
            title="Formation lanceur menhir",
            organization=orga_bodyb,
        )
        factories.CourseFactory(
            title="Formation assommeur de Romains",
            organization=orga_bodyb,
        )

        # Now we link products to courses and add course runs
        # link two products to druid course
        # one only enrollment
        course_product_druid = factories.CourseProductFactory(
            course=druid_course,
            product=become_druid_product,
        )
        course_product_druid.course_runs.add(basics_of_botany)
        course_product_druid.course_runs.add(basics_druidic)
        course_product_druid.course_runs.add(magic_potion)
        # one with certification
        course_product_druid_credential = factories.CourseProductFactory(
            course=druid_course,
            product=druid_credential_product,
            certificate_definition=factories.CertificateDefinitionFactory(title="Druide Certification"),
        )
        course_product_druid_credential.course_runs.add(basics_of_botany)
        course_product_druid_credential.course_runs.add(basics_druidic)
        course_product_druid_credential.course_runs.add(magic_potion)

        # TODO: define a course product for fishing
        # TODO: it possible to have various course run for same thing with various run dates
        # TODO: products_factories.CourseProductFactory(course=)

        #
        course_product_hunting = factories.CourseProductFactory(
            course=hunting_course,
            product=become_hunter_product,
        )
        course_product_hunting.course_runs.add(hunt_boar)
        course_product_hunting.course_runs.add(archery)

        # add course runs and position inside a course product
        factories.ProductCourseRunPositionFactory(
            course_run=basics_druidic, position=1, course_product=course_product_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=basics_of_botany, position=2, course_product=course_product_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=magic_potion, position=3, course_product=course_product_druid,
        )

        factories.ProductCourseRunPositionFactory(
            course_run=basics_druidic,
            position=1,
            course_product=course_product_druid_credential,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=basics_of_botany,
            position=2,
            course_product=course_product_druid_credential,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=magic_potion,
            position=3,
            course_product=course_product_druid_credential,
        )

        self.stdout.write(self.style.SUCCESS('Successfully fun data creation'))
