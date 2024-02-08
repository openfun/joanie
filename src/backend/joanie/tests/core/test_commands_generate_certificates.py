"""Test suite for the management command 'generate_certificates'"""
import uuid

from django.core.management import call_command
from django.test import TestCase

from joanie.core import enums, factories, models


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
        order.submit()
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
        order.submit()
        certificate_qs = models.Certificate.objects.filter(order=order)

        self.assertEqual(certificate_qs.count(), 0)

        # Calling command should generate one certificate
        call_command("generate_certificates")
        self.assertEqual(certificate_qs.count(), 1)

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
            order.submit()
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
            order.submit()
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
            order.submit()
        certificate_qs = models.Certificate.objects.filter(order__in=orders)

        self.assertEqual(certificate_qs.count(), 0)

        # A certificate should be generated for the 1st product
        with self.assertNumQueries(19):
            call_command("generate_certificates", product=product_1.id)
        self.assertEqual(certificate_qs.filter(order=orders[0]).count(), 1)
        self.assertEqual(certificate_qs.filter(order=orders[1]).count(), 0)

        # Then a certificate should be generated for the 2nd product
        with self.assertNumQueries(19):
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
            order.submit()
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
            order.submit()
        certificate_qs = models.Certificate.objects.filter(order__in=orders)

        self.assertEqual(certificate_qs.count(), 0)

        # A certificate should be generated for the 1st product
        with self.assertNumQueries(19):
            call_command("generate_certificates", product=product_1.id)
        self.assertEqual(certificate_qs.filter(order=orders[0]).count(), 1)
        self.assertEqual(certificate_qs.filter(order=orders[1]).count(), 0)

        # Then a certificate should be generated for the 2nd product
        with self.assertNumQueries(19):
            call_command("generate_certificates", product=product_2.id)
        self.assertEqual(certificate_qs.filter(order=orders[1]).count(), 1)
