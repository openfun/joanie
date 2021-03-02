import arrow
from datetime import datetime, timedelta
import jwt

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import translation

from joanie.core import enums
from joanie.core import factories
from joanie.core import models


OPENEDX_COURSE_RUN_URI = "http://openedx.test/courses/course-v1:edx+%s/course"


# TODO: rewrite tests with Happy Days references!
class APITestCase(TestCase):

    def setUp(self):
        super().setUp()
        translation.activate('en')
        # First create a course product to learn how to become a good druid
        # 1/ some course runs are required to became a good druid
        self.bases_of_botany_session1 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI % '000001+BasesOfBotany_Session1',
            start=arrow.utcnow().shift(days=-2).datetime,
        )
        self.bases_of_botany_session2 = factories.CourseRunFactory(
            title="Bases of botany",
            resource_link=OPENEDX_COURSE_RUN_URI % '000001+BasesOfBotany_Session2',
            start=arrow.utcnow().shift(days=10).datetime,
        )
        self.bases_of_druidism_session1 = factories.CourseRunFactory(
            title="Bases of druidism",
            resource_link=OPENEDX_COURSE_RUN_URI % '000002+BasesOfDruidism_Session1',
        )
        self.bases_of_druidism_session2 = factories.CourseRunFactory(
            title="Bases of druidism",
            resource_link=OPENEDX_COURSE_RUN_URI % '000002+BasesOfDruidism_Session2',
        )
        self.diy_magic_potion_session1 = factories.CourseRunFactory(
            title="How to cook a magic potion",
            resource_link=OPENEDX_COURSE_RUN_URI % '000003+DIYMagicPotion_Session1',
        )
        self.diy_magic_potion_session2 = factories.CourseRunFactory(
            title="How to cook a magic potion",
            resource_link=OPENEDX_COURSE_RUN_URI % '000003+DIYMagicPotion_Session2',
        )
        # 2/ Create the enrollment Product
        become_druid_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_ENROLLMENT,
            title="Become druid",
        )
        # 3/ Create the Course of organization "the Druid School"
        self.druid_course = factories.CourseFactory(
            title="Druid course",
            organization=factories.OrganizationFactory(title="the Druid School"),
        )
        # 4/ now link the Product to the Druid Course
        self.course_product_druid = factories.CourseProductFactory(
            course=self.druid_course,
            product=become_druid_product,
        )
        # 5/ add all course runs available for this course product
        self.course_product_druid.course_runs.add(self.bases_of_botany_session1)
        self.course_product_druid.course_runs.add(self.bases_of_druidism_session1)
        self.course_product_druid.course_runs.add(self.diy_magic_potion_session1)

        self.course_product_druid.course_runs.add(self.bases_of_botany_session2)
        self.course_product_druid.course_runs.add(self.bases_of_druidism_session2)
        self.course_product_druid.course_runs.add(self.diy_magic_potion_session2)

        # 6/ now define position of each course runs to complete the course
        # first to do
        factories.ProductCourseRunPositionFactory(
            course_run=self.bases_of_botany_session1,
            position=1,
            course_product=self.course_product_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=self.bases_of_botany_session2,
            position=1,
            course_product=self.course_product_druid,
        )
        # third to do
        factories.ProductCourseRunPositionFactory(
            course_run=self.diy_magic_potion_session1,
            position=3,
            course_product=self.course_product_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=self.diy_magic_potion_session2,
            position=3,
            course_product=self.course_product_druid,
        )
        # second to do
        factories.ProductCourseRunPositionFactory(
            course_run=self.bases_of_druidism_session1,
            position=2,
            course_product=self.course_product_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=self.bases_of_druidism_session2,
            position=2,
            course_product=self.course_product_druid,
        )

        # Now create a course product to learn how to become a good druid and get a certificate
        # 1/ Create the credential Product
        become_certified_druid = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            title="Become a certified druid",
        )
        # 2/ now link the Product to the Druid Course
        self.course_product_certified_druid = factories.CourseProductFactory(
            course=self.druid_course,
            product=become_certified_druid,
            certificate_definition=factories.CertificateDefinitionFactory(
                title="Druid Certification",
            ),
        )
        # 3/ add all course runs available for this course product
        self.course_product_certified_druid.course_runs.add(self.bases_of_botany_session1)
        self.course_product_certified_druid.course_runs.add(self.bases_of_druidism_session1)
        self.course_product_certified_druid.course_runs.add(self.diy_magic_potion_session1)

        self.course_product_certified_druid.course_runs.add(self.bases_of_botany_session2)
        self.course_product_certified_druid.course_runs.add(self.bases_of_druidism_session2)
        self.course_product_certified_druid.course_runs.add(self.diy_magic_potion_session2)

        # 6/ now define position of each course runs to complete the course
        # first to do
        factories.ProductCourseRunPositionFactory(
            course_run=self.bases_of_botany_session1,
            position=1,
            course_product=self.course_product_certified_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=self.bases_of_botany_session2,
            position=1,
            course_product=self.course_product_certified_druid,
        )
        # second to do
        factories.ProductCourseRunPositionFactory(
            course_run=self.bases_of_druidism_session1,
            position=2,
            course_product=self.course_product_certified_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=self.bases_of_druidism_session2,
            position=2,
            course_product=self.course_product_certified_druid,
        )
        # third to do
        factories.ProductCourseRunPositionFactory(
            course_run=self.diy_magic_potion_session1,
            position=3,
            course_product=self.course_product_certified_druid,
        )
        factories.ProductCourseRunPositionFactory(
            course_run=self.diy_magic_potion_session2,
            position=3,
            course_product=self.course_product_certified_druid,
        )

    def _get_order_data(self):
        # we choose to take the 3 default course runs for the druid course (session1)
        # so we give the CourseProduct uid and all resource_links of course runs selected
        return {
            'id': self.course_product_druid.uid,
            'resource_links': [
                self.bases_of_botany_session1.resource_link,
                self.bases_of_druidism_session1.resource_link,
                self.diy_magic_potion_session1.resource_link,
            ]
        }

    @staticmethod
    def _mock_user_token(username, expired_at=None):
        issued_at = datetime.utcnow()
        token = jwt.encode(
            {
                "email": f"{username}@funmooc.fr",
                "username": username,
                "exp": expired_at or issued_at + timedelta(days=2),
                "iat": issued_at,
            },
            getattr(settings, "JWT_PRIVATE_SIGNING_KEY"),
            algorithm=getattr(settings, "JWT_ALGORITHM"),
        )
        return token

    def test_get_products_available_for_a_course(self):
        # Get all products available for druid course
        response = self.client.get(f'/api/courses/{self.druid_course.code}/products')
        self.assertEqual(response.status_code, 200)
        # two products are available: course_product_druid and course_product_certified_druid
        self.assertEqual(response.data[0]['id'], str(self.course_product_druid.uid))
        self.assertEqual(
            response.data[0]['title'],
            self.course_product_druid.product.title,
        )
        self.assertEqual(
            response.data[0]['call_to_action'],
            self.course_product_druid.product.call_to_action_label,
            "let's go!",
        )
        # 2 sessions are available for each course run (2x3)
        self.assertEqual(len(response.data[0]['course_runs']), 6)

        # check ordering by position then start date
        self.assertEqual(response.data[0]['course_runs'][0]['position'], 1)
        self.assertEqual(response.data[0]['course_runs'][-1]['position'], 3)
        # check course run details returned
        self.assertEqual(
            response.data[0]['course_runs'][0]['title'],
            self.bases_of_botany_session1.title,
        )
        self.assertEqual(
            response.data[0]['course_runs'][0]['resource_link'],
            self.bases_of_botany_session1.resource_link,
        )
        self.assertEqual(response.data[1]['id'], str(self.course_product_certified_druid.uid))
        self.assertEqual(
            response.data[1]['title'],
            self.course_product_certified_druid.product.title,
        )
        # 2 sessions are available for each course run (2x3)
        self.assertEqual(len(response.data[1]['course_runs']), 6)

    def test_set_order_without_authorization(self):
        # Try to set order without Authorization
        response = self.client.post(
            '/api/orders/',
            data=self._get_order_data(),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_set_order_with_bad_token(self):
        # Try to set order with bad token
        response = self.client.post(
            '/api/orders/',
            data=self._get_order_data(),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer nawak',
        )
        self.assertEqual(response.status_code, 403)

    def test_set_order_with_expired_token(self):
        # Try to set order with expired token
        token = self._mock_user_token(
            "panoramix",
            expired_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.post(
            '/api/orders/',
            data=self._get_order_data(),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 403)

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
    def test_set_order(self):
        # Set an order for the druid course to a new user Panoramix
        self.assertEqual(models.User.objects.count(), 0)

        username = "panoramix"

        # we call api with a valid token
        token = self._mock_user_token(username)
        response = self.client.post(
            '/api/orders/',
            data=self._get_order_data(),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)
        # panoramix was an unknown user, so a new user was created
        self.assertEqual(models.User.objects.get().username, username)

        # an order was created at pending state
        order = models.Order.objects.get()
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)
        # the 3 course runs selected was linked to the order
        self.assertEqual(order.course_runs.count(), 3)
        # 3 enrollments was created for each course run at in progress state
        self.assertEqual(models.Enrollment.objects.count(), 3)
        self.assertEqual(
            models.Enrollment.objects.filter(state=enums.ENROLLMENT_STATE_IN_PROGRESS).count(),
            3,
        )
        # api return details about order just created
        order_data = response.data
        self.assertEqual(order_data['id'], str(order.uid))
        self.assertEqual(order_data['owner'], username)
        self.assertEqual(order_data['product_id'], str(self.course_product_druid.uid))
        self.assertEqual(len(order_data['enrollments']), 3)
        self.assertEqual(
            order_data['enrollments'][0]['position'],
            1,
        )
        self.assertEqual(
            order_data['enrollments'][0]['resource_link'],
            self.bases_of_botany_session1.resource_link,
        )
        self.assertEqual(
            order_data['enrollments'][0]['state'],
            enums.ENROLLMENT_STATE_IN_PROGRESS,
        )
        self.assertEqual(
            order_data['enrollments'][-1]['position'],
            3,
        )
        self.assertEqual(
            order_data['enrollments'][-1]['resource_link'],
            self.diy_magic_potion_session1.resource_link,
        )
        self.assertEqual(
            order_data['enrollments'][-1]['state'],
            enums.ENROLLMENT_STATE_IN_PROGRESS,
        )

        # Now try to enroll again, check error raising
        response = self.client.post(
            '/api/orders/',
            data=self._get_order_data(),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 403)
        # no more order
        self.assertEqual(models.Order.objects.count(), 1)
        # no more enrollments
        self.assertEqual(models.Enrollment.objects.count(), 3)
        # return an error message
        self.assertEqual(response.data["errors"], ('Order already exist',))

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
    def test_get_orders(self):
        username = "panoramix"
        token = self._mock_user_token(username)
        self.client.post(
            '/api/orders/',
            data=self._get_order_data(),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        order = models.Order.objects.get()

        # We want to test GET /api/orders/ return for user
        response = self.client.get(
            '/api/orders/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)
        # check pagination
        self.assertEqual(response.data['count'], 1)
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        # check results returned
        self.assertEqual(response.data['results'][0]['id'], str(order.uid))
        self.assertEqual(response.data['results'][0]['owner'], username)
        self.assertEqual(
            response.data['results'][0]['product_id'],
            str(self.course_product_druid.uid),
        )
        self.assertEqual(models.Enrollment.objects.count(), 3)
        self.assertEqual(
            models.Enrollment.objects.filter(state=enums.ENROLLMENT_STATE_IN_PROGRESS).count(),
            3,
        )
        order_data = response.data['results'][0]
        self.assertEqual(len(order_data['enrollments']), 3)
        self.assertEqual(
            order_data['enrollments'][0]['position'],
            1,
        )
        self.assertEqual(
            order_data['enrollments'][0]['resource_link'],
            self.bases_of_botany_session1.resource_link,
        )
        self.assertEqual(
            order_data['enrollments'][0]['state'],
            enums.ENROLLMENT_STATE_IN_PROGRESS,
        )
        self.assertEqual(
            order_data['enrollments'][-1]['position'],
            3,
        )
        self.assertEqual(
            order_data['enrollments'][-1]['resource_link'],
            self.diy_magic_potion_session1.resource_link,
        )
        self.assertEqual(
            order_data['enrollments'][-1]['state'],
            enums.ENROLLMENT_STATE_IN_PROGRESS,
        )

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
    def test_set_order_to_one_invalid_course_run(self):
        # Try to enroll to a course run with invalid resource_link

        # initialize an invalid course run
        resource_link_invalid = "http://mysterious.uri/courses/course-v0:001+Stuff_Session/course"
        invalid_course_run = factories.CourseRunFactory(
            title="How to do some stuff?",
            resource_link=resource_link_invalid,
        )
        # add invalid course run to the desired product
        self.course_product_druid.course_runs.add(invalid_course_run)
        factories.ProductCourseRunPositionFactory(
            course_run=invalid_course_run,
            position=4,
            course_product=self.course_product_druid,
        )

        # ask to enroll to the product
        username = "panoramix"
        token = self._mock_user_token(username)
        data = {
            'id': self.course_product_druid.uid,
            'resource_links': [
                invalid_course_run.resource_link,
                self.bases_of_botany_session1.resource_link,
                self.bases_of_druidism_session1.resource_link,
                self.diy_magic_potion_session1.resource_link,
            ]
        }
        with self.assertLogs(level='ERROR') as logs:
            response = self.client.post(
                '/api/orders/',
                data=data,
                content_type='application/json',
                HTTP_AUTHORIZATION=f'Bearer {token}',
            )
            msg_error = f"No LMS configuration found for resource link: {resource_link_invalid}"
            self.assertIn(msg_error, logs.output[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(models.User.objects.count(), 1)
        self.assertEqual(models.User.objects.get().username, username)

        # all joanie enrollments were created but with different states
        # and order state was set to failure
        order = models.Order.objects.get()
        self.assertEqual(order.state, enums.ORDER_STATE_FAILED)
        self.assertEqual(models.Enrollment.objects.count(), 4)
        self.assertEqual(
            models.Enrollment.objects.get(course_run__resource_link=resource_link_invalid).state,
            enums.ENROLLMENT_STATE_FAILED,
        )
        self.assertEqual(
            models.Enrollment.objects.filter(state=enums.ENROLLMENT_STATE_IN_PROGRESS).count(),
            3,
        )
        order_data = response.data
        self.assertEqual(order_data['id'], str(order.uid))
        self.assertEqual(order_data['owner'], username)
        self.assertEqual(order_data['product_id'], str(self.course_product_druid.uid))
        self.assertEqual(order_data['state'], enums.ORDER_STATE_FAILED)
        self.assertEqual(len(order_data['enrollments']), 4)
        self.assertEqual(
            order_data['enrollments'][0]['resource_link'],
            resource_link_invalid,
        )
        self.assertEqual(
            order_data['enrollments'][0]['state'],
            enums.ENROLLMENT_STATE_FAILED,
        )
        self.assertEqual(
            order_data['enrollments'][0]['position'],
            4,
        )
        self.assertEqual(
            order_data['enrollments'][1]['resource_link'],
            self.bases_of_botany_session1.resource_link,
        )
        self.assertEqual(
            order_data['enrollments'][1]['state'],
            enums.ENROLLMENT_STATE_IN_PROGRESS,
        )
        self.assertEqual(
            order_data['enrollments'][1]['position'],
            1,
        )

    # TODO: add test with course run not available for the course product
    def test_set_order_to_course_run_not_available_for_the_course_product(self):
        pass
