# pylint: disable=unexpected-keyword-arg,no-value-for-parameter
"""Test suite for the management command 'generate_certificates'"""

import uuid
from http import HTTPStatus
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

import responses

from joanie.core import enums, factories, models
from joanie.lms_handler import LMSHandler


class CreateCertificatesTestCase(TestCase):
    """Test case for the management command 'generate_certificates'"""

    def test_commands_generate_certificates_has_options(
        self,
    ):  # pylint: disable=no-self-use
        """
        This command should accept three optional arguments:
            - courses
            - products
            - orders
        """
        options = {
            "courses": "00000",
            "orders": uuid.uuid4(),
            "products": uuid.uuid4(),
        }

        # TypeError: Unknown option(s) should not be raised
        call_command("generate_certificates", **options)

    def test_commands_generate_certificates_for_credential_product(self):
        """
        The management command should generate certificates for the credential
        type of product.
        If a certifying product contains graded courses with gradable course runs
        and a user purchased this product and passed all gradable course runs,
        a certificate should be generated
        """

        # Create a certifying product with one order eligible for certification
        course_run = factories.CourseRunFactory(
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        order = factories.OrderFactory(product=product)
        order.init_flow()
        certificate_qs = models.Certificate.objects.filter(order=order)

        self.assertEqual(certificate_qs.count(), 0)

        # Calling command should generate one certificate
        call_command("generate_certificates")
        self.assertEqual(certificate_qs.count(), 1)

        # But call it again, should not create a new certificate
        call_command("generate_certificates")
        self.assertEqual(certificate_qs.count(), 1)

    def test_commands_generate_certificates_for_certificate_product(self):
        """
        The management command should generate certificates for the certificate
        type of product.
        """
        course_run = factories.CourseRunFactory(
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
            is_listed=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type="certificate",
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course_run.course],
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        order = factories.OrderFactory(
            product=product, course=None, enrollment=enrollment, owner=enrollment.user
        )
        order.init_flow()
        certificate_qs = models.Certificate.objects.filter(order=order)

        self.assertEqual(certificate_qs.count(), 0)

        # Calling command should generate one certificate
        call_command("generate_certificates")
        self.assertEqual(certificate_qs.count(), 1)

        # But call it again, should not create a new certificate
        call_command("generate_certificates")
        self.assertEqual(certificate_qs.count(), 1)

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
                "BASE_URL": "http://moodle.test/webservice/rest/server.php",
                "COURSE_REGEX": r"^.*/course/view.php\?id=.*$",
                "SELECTOR_REGEX": r"^.*/course/view.php\?id=.*$",
            },
        ]
    )
    @mock.patch("joanie.core.models.courses.Enrollment.set")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_commands_generate_certificates_for_certificate_product_with_moodle_enrollment(
        self, _
    ):
        """
        The management command should generate certificates for the certificate
        type of product relying on moodle enrollment.
        """
        passed_resource_link = "http://moodle.test/course/view.php?id=1"
        failed_resource_link = "http://moodle.test/course/view.php?id=2"
        lms_backend = LMSHandler.select_lms(passed_resource_link)

        responses.add(
            responses.POST,
            lms_backend.build_url("core_user_get_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "criteria[0][key]": "username",
                        "criteria[0][value]": "student",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json={
                "users": [
                    {
                        "id": 5,
                        "username": "student",
                        "firstname": "Student",
                        "lastname": "User",
                        "fullname": "Student User",
                        "email": "student@example.com",
                        "department": "",
                        "firstaccess": 1704716076,
                        "lastaccess": 1704716076,
                        "auth": "manual",
                        "suspended": False,
                        "confirmed": True,
                        "lang": "en",
                        "theme": "",
                        "timezone": "99",
                        "mailformat": 1,
                        "description": "",
                        "descriptionformat": 1,
                        "profileimageurlsmall": (
                            "https://moodle.test/theme/image.php/boost/core/1704714971/u/f2"
                        ),
                        "profileimageurl": (
                            "https://moodle.test/theme/image.php/boost/core/1704714971/u/f1"
                        ),
                    }
                ],
                "warnings": [],
            },
        )

        # Response for the passed run
        responses.add(
            responses.POST,
            lms_backend.build_url("core_completion_get_course_completion_status"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "courseid": "1",
                        "userid": "5",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json={
                "completionstatus": {
                    "completed": True,
                    "aggregation": 1,
                    "completions": [
                        {
                            "type": 4,
                            "title": "Activity completion",
                            "status": "Yes",
                            "complete": True,
                            "timecompleted": 1705067787,
                            "details": {
                                "type": "Activity completion",
                                "criteria": (
                                    '<a href="https://moodle.test/mod/quiz/view.php?id=3">'
                                    "Quizz 1"
                                    "</a>"
                                ),
                                "requirement": "Marking yourself complete",
                                "status": "",
                            },
                        },
                        {
                            "type": 4,
                            "title": "Activity completion",
                            "status": "Yes",
                            "complete": True,
                            "timecompleted": 1705067739,
                            "details": {
                                "type": "Activity completion",
                                "criteria": (
                                    '<a href="https://moodle.test/mod/quiz/view.php?id=4">'
                                    "Quizz 2"
                                    "</a>"
                                ),
                                "requirement": "Marking yourself complete",
                                "status": "",
                            },
                        },
                    ],
                },
                "warnings": [],
            },
        )

        # Response for the failed run
        responses.add(
            responses.POST,
            lms_backend.build_url("core_completion_get_course_completion_status"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "courseid": "2",
                        "userid": "5",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json={
                "completionstatus": {
                    "completed": False,
                    "aggregation": 0,
                    "completions": [
                        {
                            "type": 4,
                            "title": "Activity completion",
                            "status": "No",
                            "complete": False,
                            "timecompleted": 1705067787,
                            "details": {
                                "type": "Activity completion",
                                "criteria": (
                                    '<a href="https://moodle.test/mod/quiz/view.php?id=3">'
                                    "Quizz 1"
                                    "</a>"
                                ),
                                "requirement": "Marking yourself complete",
                                "status": "",
                            },
                        },
                    ],
                },
                "warnings": [],
            },
        )
        organization = factories.OrganizationFactory()
        passed_course_run = factories.CourseRunFactory(
            course__organizations=[organization],
            resource_link=passed_resource_link,
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
            is_listed=True,
        )
        failed_course_run = factories.CourseRunFactory(
            course__organizations=[organization],
            resource_link=failed_resource_link,
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
            is_listed=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type="certificate",
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[failed_course_run.course, passed_course_run.course],
        )
        user = factories.UserFactory(username="student")
        # Passed certificate
        enrollment = factories.EnrollmentFactory(
            course_run=passed_course_run, is_active=True, user=user
        )
        passed_order = factories.OrderFactory(
            product=product, course=None, enrollment=enrollment, owner=user
        )
        passed_order.init_flow()
        # Failed certificate
        enrollment = factories.EnrollmentFactory(
            course_run=failed_course_run, is_active=True, user=user
        )
        failed_order = factories.OrderFactory(
            product=product, course=None, enrollment=enrollment, owner=user
        )
        failed_order.init_flow()

        certificate_qs = models.Certificate.objects.all()
        self.assertEqual(certificate_qs.count(), 0)

        # Calling command should generate only one certificate for the passed course run
        call_command("generate_certificates")
        self.assertEqual(certificate_qs.count(), 1)
        passed_order.refresh_from_db()
        self.assertEqual(passed_order.certificate.id, certificate_qs.first().id)

        # But call it again, should not create a new certificate
        call_command("generate_certificates")
        self.assertEqual(certificate_qs.count(), 1)

    def test_commands_generate_certificates_can_be_restricted_to_order(self):
        """
        If `order` option is used, the review is restricted to it.
        """
        # Create a certifying product with two orders eligible for certification
        course_run = factories.CourseRunFactory(
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        course = factories.CourseFactory(products=[product])
        orders = factories.OrderFactory.create_batch(2, product=product, course=course)
        for order in orders:
            order.init_flow()
        certificate_qs = models.Certificate.objects.filter(order__in=orders)

        self.assertEqual(certificate_qs.count(), 0)

        # A certificate should be generated for the 1st order
        call_command("generate_certificates", order=orders[0].id)
        self.assertEqual(certificate_qs.filter(order=orders[0]).count(), 1)

        # Then a certificate should be generated for the 2nd order
        call_command("generate_certificates", order=orders[1].id)
        self.assertEqual(certificate_qs.filter(order=orders[1]).count(), 1)

    def test_commands_generate_certificates_can_be_restricted_to_course(self):
        """
        If `course` option is used, the review is restricted to it.
        """
        # Create a certifying product used in two courses
        # Then create one order per course
        course_run = factories.CourseRunFactory(
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        [course_1, course_2] = factories.CourseFactory.create_batch(
            2, products=[product]
        )
        orders = [
            factories.OrderFactory(product=product, course=course_1),
            factories.OrderFactory(product=product, course=course_2),
        ]
        for order in orders:
            order.init_flow()
        certificate_qs = models.Certificate.objects.filter(order__in=orders)

        self.assertEqual(certificate_qs.count(), 0)

        # A certificate should be generated for the 1st course
        call_command("generate_certificates", course=course_1.code)
        self.assertEqual(certificate_qs.filter(order=orders[0]).count(), 1)

        # Then a certificate should be generated for the 2nd course
        call_command("generate_certificates", course=course_2.code)
        self.assertEqual(certificate_qs.filter(order=orders[1]).count(), 1)

    def test_commands_generate_certificates_can_be_restricted_to_product(self):
        """
        If `product` option is used, the review is restricted to it.
        """
        # Create two certifying products with order eligible for certification.
        [cr1, cr2] = factories.CourseRunFactory.create_batch(
            2,
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        product_1 = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[cr1.course],
        )
        product_2 = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[cr2.course],
        )
        course = factories.CourseFactory(products=[product_1, product_2])
        orders = [
            factories.OrderFactory(course=course, product=product_1),
            factories.OrderFactory(course=course, product=product_2),
        ]
        for order in orders:
            order.init_flow()
        certificate_qs = models.Certificate.objects.filter(order__in=orders)

        self.assertEqual(certificate_qs.count(), 0)

        # A certificate should be generated for the 1st product
        with self.assertNumQueries(23):
            call_command("generate_certificates", product=product_1.id)
        self.assertEqual(certificate_qs.filter(order=orders[0]).count(), 1)
        self.assertEqual(certificate_qs.filter(order=orders[1]).count(), 0)

        # Then a certificate should be generated for the 2nd product
        with self.assertNumQueries(23):
            call_command("generate_certificates", product=product_2.id)
        self.assertEqual(certificate_qs.filter(order=orders[1]).count(), 1)

    def test_commands_generate_certificates_can_be_restricted_to_product_course(self):
        """
        `product` and `course` options can be used together to restrict review to them.
        """
        # Create two certifying products with order eligible for certification.
        [cr1, cr2] = factories.CourseRunFactory.create_batch(
            2,
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        product_1 = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[cr1.course],
        )
        product_2 = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[cr2.course],
        )
        [course_1, course_2] = factories.CourseFactory.create_batch(
            2, products=[product_1, product_2]
        )

        # Create orders for each course product couples
        orders = [
            factories.OrderFactory(course=course_1, product=product_1),
            factories.OrderFactory(course=course_1, product=product_2),
            factories.OrderFactory(course=course_2, product=product_1),
            factories.OrderFactory(course=course_2, product=product_2),
        ]
        for order in orders:
            order.init_flow()
        certificate_qs = models.Certificate.objects.filter(order__in=orders)

        self.assertEqual(certificate_qs.count(), 0)

        # A certificate should be generated for the couple course_1 - product_1
        call_command(
            "generate_certificates", course=course_1.code, product=product_1.id
        )
        self.assertEqual(certificate_qs.filter(order=orders[0]).count(), 1)

        # Then a certificate should be generated for the couple course_1 - product_2
        call_command(
            "generate_certificates", course=course_1.code, product=product_2.id
        )
        self.assertEqual(certificate_qs.filter(order=orders[1]).count(), 1)

        # Then a certificate should be generated for the couple course_2 - product_1
        call_command(
            "generate_certificates", course=course_2.code, product=product_1.id
        )
        self.assertEqual(certificate_qs.filter(order=orders[2]).count(), 1)

        # Finally, a certificate should be generated for the couple course_2 - product_2
        call_command(
            "generate_certificates", course=course_2.code, product=product_2.id
        )
        self.assertEqual(certificate_qs.filter(order=orders[3]).count(), 1)

    def test_commands_generate_certificates_optimizes_db_queries(self):
        """
        The management command should optimize db access
        """
        # Create two certifying products with order eligible for certification.
        [cr1, cr2, cr3, cr4, cr5, cr6] = factories.CourseRunFactory.create_batch(
            6,
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        product_1 = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[cr1.course, cr2.course, cr3.course],
        )
        product_2 = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[cr4.course, cr5.course, cr6.course],
        )
        course = factories.CourseFactory(products=[product_1, product_2])
        orders = [
            factories.OrderFactory(course=course, product=product_1),
            factories.OrderFactory(course=course, product=product_2),
        ]
        for order in orders:
            order.init_flow()
        certificate_qs = models.Certificate.objects.filter(order__in=orders)

        self.assertEqual(certificate_qs.count(), 0)

        # A certificate should be generated for the 1st product
        with self.assertNumQueries(23):
            call_command("generate_certificates", product=product_1.id)
        self.assertEqual(certificate_qs.filter(order=orders[0]).count(), 1)
        self.assertEqual(certificate_qs.filter(order=orders[1]).count(), 0)

        # Then a certificate should be generated for the 2nd product
        with self.assertNumQueries(23):
            call_command("generate_certificates", product=product_2.id)
        self.assertEqual(certificate_qs.filter(order=orders[1]).count(), 1)
