"""Test suite utility methods for offering to get orders and certificates"""

from datetime import datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from joanie.core import enums, factories
from joanie.core.models import CourseProductRelation, CourseState
from joanie.core.utils import webhooks
from joanie.core.utils.offering import (
    get_generated_certificates,
    get_orders,
    get_serialized_course_runs,
    synchronize_offerings,
)
from joanie.tests.base import LoggingTestCase


class UtilsCourseProductRelationTestCase(LoggingTestCase):
    """Test suite utility methods for offering to get orders and certificates"""

    maxDiff = None

    def test_utils_offering_get_orders_for_product_type_credential(self):
        """
        It should return the list of orders ids that are completed for this offering
        with a product of type credential where the certificate has not been published yet.
        """
        course = factories.CourseFactory()
        factories.CourseRunFactory(
            course=course,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            price=0,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            courses=[course],
        )
        offering = CourseProductRelation.objects.get(product=product, course=course)
        # Generate orders for the offering with the course
        factories.OrderFactory.create_batch(
            10,
            product=offering.product,
            course=offering.course,
            enrollment=None,
            state=enums.ORDER_STATE_COMPLETED,
        )

        result = get_orders(offering=offering)

        self.assertEqual(len(result), 10)

    def test_utils_offering_get_orders_for_product_type_certificate(
        self,
    ):
        """
        It should return the list of orders ids that are completed for the offering
        with a product of type certificate where the certificate has not been published yet.
        """
        course_run = factories.CourseRunFactory(
            is_gradable=True, is_listed=True, state=CourseState.ONGOING_OPEN
        )
        enrollments = factories.EnrollmentFactory.create_batch(5, course_run=course_run)
        product = factories.ProductFactory(
            price=0,
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )
        offering = factories.OfferingFactory(
            product=product, course=enrollments[0].course_run.course
        )

        orders = get_orders(offering=offering)

        self.assertEqual(len(orders), 0)

        # Generate orders for the offering with the enrollments
        for enrollment in enrollments:
            factories.OrderFactory(
                product=offering.product,
                enrollment=enrollment,
                course=None,
                state=enums.ORDER_STATE_COMPLETED,
            )

        orders = get_orders(offering=offering)

        self.assertEqual(len(orders), 5)

    def test_utils_offering_get_generated_certificates_for_product_type_credential(
        self,
    ):
        """
        It should return the amount of certificates that were published for this course product
        offering with a product of type credential.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            price=0,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            courses=[course],
        )
        factories.CourseRunFactory(
            course=course,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
            is_gradable=True,
        )
        offering = CourseProductRelation.objects.get(product=product, course=course)

        generated_certificates_queryset = get_generated_certificates(offering=offering)

        self.assertEqual(generated_certificates_queryset.count(), 0)

        # Generate certificates for the offering
        orders = factories.OrderFactory.create_batch(
            5,
            product=offering.product,
            course=offering.course,
            enrollment=None,
            state=enums.ORDER_STATE_COMPLETED,
        )
        for order in orders:
            factories.OrderCertificateFactory(order=order)

        generated_certificates_queryset = get_generated_certificates(offering=offering)

        self.assertEqual(generated_certificates_queryset.count(), 5)

    def test_utils_offering_get_generated_certificated_for_product_type_certificate(
        self,
    ):
        """
        It should return the amount of certificates that were published for this course product
        offering with a product of type certificate.
        """
        course_run = factories.CourseRunFactory(
            is_gradable=True, is_listed=True, state=CourseState.ONGOING_OPEN
        )
        enrollments = factories.EnrollmentFactory.create_batch(
            10, course_run=course_run
        )
        product = factories.ProductFactory(price=0, type=enums.PRODUCT_TYPE_CERTIFICATE)
        offering = factories.OfferingFactory(
            product=product, course=enrollments[0].course_run.course
        )

        generated_certificates_queryset = get_generated_certificates(offering=offering)

        self.assertEqual(generated_certificates_queryset.count(), 0)

        # Generate certificates for the offering
        for enrollment in enrollments:
            factories.OrderCertificateFactory(
                order=factories.OrderFactory(
                    product=offering.product,
                    enrollment=enrollment,
                    course=None,
                    state=enums.ORDER_STATE_COMPLETED,
                )
            )

        generated_certificates_queryset = get_generated_certificates(offering=offering)

        self.assertEqual(generated_certificates_queryset.count(), 10)

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_utils_offering_synchronize_offerings(self, mock_sync):
        """
        It should return the list of course product relations that have offering rules
        that start or end in the next 60 minutes, with distinct offerings.
        """
        mocked_now = datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC"))

        course_1 = factories.CourseFactory(
            course_runs=factories.CourseRunFactory.create_batch(3)
        )
        offering_rule_starts_in_10_min = factories.OfferingRuleFactory(
            start=mocked_now + timedelta(minutes=10),
            course_product_relation=factories.OfferingFactory(
                course=course_1,
                product=factories.ProductFactory(
                    type=enums.PRODUCT_TYPE_CREDENTIAL, target_courses=[course_1]
                ),
            ),
        )
        offering_1 = offering_rule_starts_in_10_min.offering

        # Only distinct offerings (course_product_relation) should be returned
        factories.OfferingRuleFactory(
            start=mocked_now + timedelta(minutes=59),
            course_product_relation=offering_rule_starts_in_10_min.course_product_relation,
        )

        offering_rule_ends_in_10_min = factories.OfferingRuleFactory(
            end=mocked_now + timedelta(minutes=10),
        )
        offering_2 = offering_rule_ends_in_10_min.offering
        course_3 = factories.CourseFactory(
            course_runs=factories.CourseRunFactory.create_batch(1)
        )
        offering_rule_ends_in_59_min = factories.OfferingRuleFactory(
            end=mocked_now + timedelta(minutes=59),
            course_product_relation=factories.OfferingFactory(
                course=course_3,
                product=factories.ProductFactory(
                    type=enums.PRODUCT_TYPE_CREDENTIAL, target_courses=[course_3]
                ),
            ),
        )
        offering_3 = offering_rule_ends_in_59_min.offering

        mock_sync.reset_mock()

        with (
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
            self.record_performance(),
            self.assertLogs() as logger,
        ):
            synchronize_offerings.run()

        synchronized_course_runs = mock_sync.call_args_list[0][0][0]

        self.assertLogsEquals(
            logger.records,
            [
                ("INFO", "Synchronizing 3 offerings"),
                ("INFO", f"Get serialized course runs for offering {offering_3.id}"),
                ("INFO", "  1 course runs serialized"),
                ("INFO", f"Get serialized course runs for offering {offering_2.id}"),
                ("INFO", "  No course runs serialized"),
                ("INFO", f"Get serialized course runs for offering {offering_1.id}"),
                # One equivalent course run per offering, whatever its number of sessions
                ("INFO", "  1 course runs serialized"),
                ("INFO", "Synchronizing 2 course runs for offerings"),
            ],
        )

        self.assertEqual(len(synchronized_course_runs), 2)
        self.assertEqual(
            synchronized_course_runs[0]["resource_link"],
            f"https://example.com/api/v1.0/courses/{offering_3.course.code}/"
            f"products/{offering_3.product.id}/",
        )
        self.assertEqual(
            synchronized_course_runs[1]["resource_link"],
            f"https://example.com/api/v1.0/courses/{offering_1.course.code}/"
            f"products/{offering_1.product.id}/",
        )

    def test_utils_offering_get_serialized_course_runs_credential_restricted_course_runs(
        self,
    ):
        """
        A credential offering should be synchronized with one single course run, equivalent
        to the course runs targeted by the product. The other course runs of the course
        (here an older one, closed to enrollment) share the offering uri as resource link, so
        sending them would overwrite the right one in the remote catalog.
        """
        course = factories.CourseFactory()
        closed_course_run = factories.CourseRunFactory(
            course=course, state=CourseState.ONGOING_CLOSED, is_listed=True
        )
        open_course_run = factories.CourseRunFactory(
            course=course, state=CourseState.FUTURE_OPEN, is_listed=False
        )
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            courses=[course],
            target_courses=[course],
            price=300,
        )
        product.target_course_relations.get(course=course).course_runs.set(
            [open_course_run]
        )
        offering = product.offerings.get()

        serialized_course_runs = get_serialized_course_runs(
            offering, visibility=enums.COURSE_AND_SEARCH
        )

        self.assertEqual(len(serialized_course_runs), 1)
        self.assertEqual(serialized_course_runs[0]["resource_link"], offering.uri)
        self.assertEqual(
            serialized_course_runs[0]["enrollment_end"],
            open_course_run.enrollment_end.isoformat(),
        )
        self.assertEqual(
            serialized_course_runs[0]["start"], open_course_run.start.isoformat()
        )
        self.assertNotEqual(
            serialized_course_runs[0]["enrollment_end"],
            closed_course_run.enrollment_end.isoformat(),
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_utils_offering_synchronize_certificate(self, mock_sync):
        """
        It should synchronize the course runs of a certificate product.
        """
        mocked_now = datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
        course = factories.CourseFactory()

        course_run = factories.CourseRunFactory(
            course=course,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
        )

        certificate_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            courses=[course_run.course],
            target_courses=[],
            certificate_definition=factories.CertificateDefinitionFactory(
                title="Certification",
                name="Become a certified learner certificate",
            ),
            price=100,
        )
        offering = certificate_product.offerings.first()
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            start=mocked_now + timedelta(minutes=10),
        )
        mock_sync.reset_mock()

        with (
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
            self.record_performance(),
            self.assertLogs() as logger,
        ):
            synchronize_offerings.run()

        self.assertLogsEquals(
            logger.records,
            [
                ("INFO", "Synchronizing 1 offerings"),
                ("INFO", f"Get serialized course runs for offering {offering.id}"),
                ("INFO", "  1 course runs serialized"),
                ("INFO", "Synchronizing 1 course runs for offerings"),
            ],
        )

        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(len(synchronized_course_runs), 1)
        synchronized_course_run = synchronized_course_runs[0]
        self.assertEqual(
            synchronized_course_run,
            {
                "catalog_visibility": enums.COURSE_AND_SEARCH,
                "certificate_discount": offering.rules.get("discount"),
                "certificate_discounted_price": offering.rules.get("discounted_price"),
                "certificate_offer": enums.COURSE_OFFER_PAID,
                "certificate_price": certificate_product.price,
                "course": course_run.course.code,
                "discount": None,
                "discounted_price": None,
                "start": course_run.start.isoformat(),
                "end": course_run.end.isoformat(),
                "enrollment_start": course_run.enrollment_start.isoformat(),
                "enrollment_end": course_run.enrollment_end.isoformat(),
                "languages": course_run.languages,
                "offer": enums.COURSE_OFFER_FREE,
                "price": None,
                "resource_link": f"https://example.com/api/v1.0/course-runs/{course_run.id}/",
            },
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_utils_offering_synchronize_credential(self, mock_sync):
        """
        It should synchronize the course runs of a credential product.
        """
        mocked_now = datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
        course = factories.CourseFactory()

        course_run = factories.CourseRunFactory(
            course=course,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )

        credential_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            courses=[course_run.course],
            target_courses=[course_run.course],
            certificate_definition=factories.CertificateDefinitionFactory(
                title="Certification",
                name="Become a certified learner certificate",
            ),
            price=100,
        )
        offering = credential_product.offerings.first()
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            start=mocked_now + timedelta(minutes=10),
        )
        course_run.save()
        mock_sync.reset_mock()

        with (
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
            self.record_performance(),
            self.assertLogs() as logger,
        ):
            synchronize_offerings.run()

        self.assertLogsEquals(
            logger.records,
            [
                ("INFO", "Synchronizing 1 offerings"),
                ("INFO", f"Get serialized course runs for offering {offering.id}"),
                ("INFO", "  1 course runs serialized"),
                ("INFO", "Synchronizing 1 course runs for offerings"),
            ],
        )

        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(len(mock_sync.call_args_list), 1)
        synchronized_course_run = synchronized_course_runs[0]
        self.assertEqual(
            synchronized_course_run,
            {
                "catalog_visibility": enums.COURSE_AND_SEARCH,
                "certificate_offer": enums.COURSE_OFFER_PAID,
                "course": course_run.course.code,
                "discount": offering.rules.get("discount"),
                "discounted_price": offering.rules.get("discounted_price"),
                "start": course_run.start.isoformat(),
                "end": course_run.end.isoformat(),
                "enrollment_start": course_run.enrollment_start.isoformat(),
                "enrollment_end": course_run.enrollment_end.isoformat(),
                "languages": course_run.languages,
                "offer": enums.COURSE_OFFER_PAID,
                "price": credential_product.price,
                "price_currency": "EUR",
                "resource_link": "https://example.com/api/v1.0/courses/"
                f"{course_run.course.code}/products/{credential_product.id}/",
            },
        )
