from unittest import TestCase

from django.db.models import Q
from joanie.core import factories, models


class TestUserCourses(TestCase):
    def test_user_courses_get_user_courses(self):
        [course1, course2] = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(course=course1)
        course_run = factories.CourseRunFactory(course=course2)

        user = factories.UserFactory()

        enrollment = factories.EnrollmentFactory(course_run=course_run, user=user)
        order = factories.OrderFactory(product=product, owner=user)

        owned_products = models.Product.objects.filter(orders__in=[user.orders])
        owned_course_runs = models.CourseRun.objects.filter(course_runs__enrollment__in=[user.enrollments])

        orders = user.orders()
        enrollments = user.enrollments.objects.filters(course_run__course__orders__not_in=[user.orders])

        return models.Course.objects.filter(ids__in=[**enrollments.course_run.course, **orders.course])

        """
        [{
            "code": 00001,
            "organization": { "code": FUN },
            "order": {}
            "enrollment": {}
        }]
        """
