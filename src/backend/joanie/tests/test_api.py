import jwt

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings


from joanie.core import enums

from joanie.core import factories

from joanie.core import models


class APITestCase(TestCase):

    def setUp(self):
        super().setUp()
        # initialize some course runs (NB: will be sync from lms)
        # TODO: set language in fr or use english label
        factories.CourseRunFactory(title="Comment assommer un romain")
        factories.CourseRunFactory(title="Comment reconnaître un romain")
        factories.CourseRunFactory(title="Apprendre à pêcher")
        factories.CourseRunFactory(
            title="Fabriquer une canne à pêche",
        )
        factories.CourseRunFactory(title="Comment soulever une charge")
        hunt_boar = factories.CourseRunFactory(title="Apprendre à pister un sanglier")
        archery = factories.CourseRunFactory(title="Apprendre à tirer à l'arc")

        openedx_lms_uri = "http://openedx.test/courses/course-v1:edx+"
        self.basics_of_botany = factories.CourseRunFactory(
            title="Le BABA de la botanique",
            resource_link=f"{openedx_lms_uri}000001+BasicBotany_Session/course",
        )
        self.basics_druidic = factories.CourseRunFactory(
            title="Le BABA druidique",
            resource_link=f"{openedx_lms_uri}000002+BasicDruidic_Session/course",
        )
        # TODO: add same course run but with other run date
        self.magic_potion = factories.CourseRunFactory(
            title="Comment faire une potion magique",
            resource_link=f"{openedx_lms_uri}000003+MagicPotion_Session/course",
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
        self.druid_course = factories.CourseFactory(
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
        self.course_product_druid = factories.CourseProductFactory(
            course=self.druid_course,
            product=become_druid_product,
        )
        self.course_product_druid.course_runs.add(self.basics_of_botany)
        self.course_product_druid.course_runs.add(self.basics_druidic)
        self.course_product_druid.course_runs.add(self.magic_potion)
        # one with certification
        self.course_product_druid_credential = factories.CourseProductFactory(
            course=self.druid_course,
            product=druid_credential_product,
        )
        self.course_product_druid_credential.course_runs.add(self.basics_of_botany)
        self.course_product_druid_credential.course_runs.add(self.basics_druidic)
        self.course_product_druid_credential.course_runs.add(self.magic_potion)

        # TODO: define a course product for fishing
        # TODO: it possible to have various course run for same thing with various run dates

        # create druid certification
        druid_certification = factories.CertificateDefinitionFactory(
            title="Druide Certification",
        )
        # link druid certification to credential product
        factories.CourseProductCertificationFactory(
            certificate_definition=druid_certification,
            course_product=self.course_product_druid_credential,
        )

        #
        course_product_hunting = factories.CourseProductFactory(
            course=hunting_course,
            product=become_hunter_product,
        )
        course_product_hunting.course_runs.add(hunt_boar)
        course_product_hunting.course_runs.add(archery)

        # add course runs and position inside a course product
        factories.ProductCourseRunPositionFactory(
            course_run=self.basics_druidic, position=1, course_product=self.course_product_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=self.basics_of_botany, position=2, course_product=self.course_product_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=self.magic_potion, position=3, course_product=self.course_product_druid,
        )

        factories.ProductCourseRunPositionFactory(
            course_run=self.basics_druidic,
            position=1,
            course_product=self.course_product_druid_credential,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=self.basics_of_botany,
            position=2,
            course_product=self.course_product_druid_credential,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=self.magic_potion,
            position=3,
            course_product=self.course_product_druid_credential,
        )

    def test_get_products_available_for_a_course(self):
        response = self.client.get(f'/api/courses/{self.druid_course.code}/products')
        self.assertEqual(response.status_code, 200)
        # check return all products for druid course:
        # course_product_druid and course_product_druid_credential
        self.assertEqual(response.data[0]['id'], str(self.course_product_druid.uid))
        self.assertEqual(
            response.data[0]['title'],
            self.course_product_druid.product.title,
        )
        self.assertEqual(
            response.data[0]['call_to_action'],
            self.course_product_druid.product.call_to_action_label,
            "let's go!",  # TODO: beurk
        )
        self.assertEqual(len(response.data[0]['course_runs']), 3)

        self.assertEqual(response.data[1]['id'], str(self.course_product_druid_credential.uid))
        self.assertEqual(
            response.data[1]['title'],
            self.course_product_druid_credential.product.title,
        )
        self.assertEqual(len(response.data[1]['course_runs']), 3)
        # TODO: test course runs data

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
                "BASE_URL": "http://openedx.test",
                "SELECTOR_REGEX": r".*openedx.test.*",
                "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            },
        ]
    )
    def test_set_order_enrollment(self):
        # first test passing an order for the druid course to user Panoramix
        # we choose to take the 3 default course runs
        self.assertEqual(models.User.objects.count(), 0)
        # todo: mock token send by cms
        username = "panoramix"
        token = jwt.encode(
            {'username': username},
            getattr(settings, "JWT_PRIVATE_SIGNING_KEY"),
            algorithm=getattr(settings, "JWT_ALGORITHM"),
        )
        self.assertEqual(len(token.split('.')), 3)
        # pass CourseProduct uid and all resource_links of course runs selected
        data = {
            'id': self.course_product_druid.uid,
            'resource_links': [
                self.basics_of_botany.resource_link,
                self.basics_druidic.resource_link,
                self.magic_potion.resource_link,
            ]
        }
        # TODO: test failure Authorization
        response = self.client.post(
            '/api/orders/',
            data=data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(models.User.objects.count(), 1)
        self.assertEqual(models.User.objects.get().username, username)
        order = models.Order.objects.get()
        self.assertEqual(order.course_runs.count(), 3)
        self.assertEqual(models.Enrollment.objects.count(), 3)
        self.assertEqual(
            set(models.Enrollment.objects.values_list('state', flat=True)),
            {enums.ENROLLMENT_STATE_IN_PROGRESS},
        )
        order_data = response.data
        self.assertEqual(order_data['id'], str(order.uid))
        self.assertEqual(order_data['owner'], username)
        self.assertEqual(order_data['product_id'], str(self.course_product_druid.uid))
        self.assertEqual(len(order_data['course_runs']), 3)
        # TODO: test course runs data

        response = self.client.get(
            '/api/orders/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)
        # check pagination
        self.assertEqual(response.data['count'], 1)
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        # check result return
        self.assertEqual(response.data['results'][0]['id'], str(order.uid))
        self.assertEqual(response.data['results'][0]['owner'], username)
        self.assertEqual(
            response.data['results'][0]['product_id'],
            str(self.course_product_druid.uid),
        )
        self.assertEqual(len(response.data['results'][0]['course_runs']), 3)
        # TODO: test course runs data
        self.assertEqual(models.Enrollment.objects.count(), 3)
        self.assertEqual(
            models.Enrollment.objects.filter(state=enums.ENROLLMENT_STATE_IN_PROGRESS).count(),
            3,
        )
        # try to enroll again, check error raising
        response = self.client.post(
            '/api/orders/',
            data=data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(models.Order.objects.count(), 1)
        self.assertEqual(models.Enrollment.objects.count(), 3)
        self.assertEqual(response.data["errors"], ('Order already exist',))

        # TODO: test with invalid resource_links/LMS configuration not found
