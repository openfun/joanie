"""Test suite for the management command `synchronize_course_runs`."""

import random
import uuid
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase

from joanie.core import enums, factories
from joanie.core.models import Product
from joanie.core.utils import webhooks


class SynchronizeCourseRunsTestCase(TestCase):
    """Test case for the management command `synchronize_course_runs`."""

    def test_commands_synchronize_course_runs_option_course_mandatory(self):
        """
        This command takes one mandatory argument 'course' which must match an existing
        course.
        """

        # If a course option is missing, a CommandError should be raised.
        with self.assertRaisesMessage(
            CommandError, "Error: the following arguments are required: --course/-c"
        ):
            call_command("synchronize_course_runs")

        # If a course code is provided but does not match an existing course, a
        # KeyError should be raised
        with self.assertRaisesMessage(
            KeyError, 'Course with code "00000" does not exist.'
        ):
            call_command("synchronize_course_runs", course="00000")

        # If a course id is provided but does not match an existing course, a
        # KeyError should be raised
        course_id = str(uuid.uuid4())
        with self.assertRaisesMessage(
            KeyError, f'Course with id "{course_id}" does not exist.'
        ):
            call_command("synchronize_course_runs", course=course_id)

    def test_commands_synchronize_course_runs_has_options(self):
        """
        This command should accept one required argument course then three optional
        arguments `course_runs`, `products` and `visibility`.
        """
        factories.CourseFactory(code="00000")

        options = {
            "course": "00000",
            "course_runs": uuid.uuid4(),
            "products": uuid.uuid4(),
            "visibility": "course_and_search",
        }

        call_command("synchronize_course_runs", **options)

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_commands_synchronize_course_runs_without_resources(self, webhook_mock):
        """
        If any course run or product are provided, the command should retrieve
        listed course runs and credential products related to the provided course.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(course=course, is_listed=True)
        factories.CourseRunFactory(course=course, is_listed=False)

        product = factories.ProductFactory(
            courses=[course], type=enums.PRODUCT_TYPE_CREDENTIAL
        )
        factories.ProductFactory(courses=[course], type=enums.PRODUCT_TYPE_CERTIFICATE)
        factories.ProductFactory(courses=[course], type=enums.PRODUCT_TYPE_ENROLLMENT)
        webhook_mock.reset_mock()

        call_command("synchronize_course_runs", course=course.code)

        webhook_mock.assert_called_once_with(
            [
                course_run.get_serialized(),
                *Product.get_equivalent_serialized_course_runs_for_products(
                    [product], courses=[course]
                ),
            ]
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_commands_synchronize_course_runs_with_course_runs(self, webhook_mock):
        """
        If course runs ids are provided, the command should synchronize only
        listed course runs matching ids.
        """
        course = factories.CourseFactory()
        listed_course_run = factories.CourseRunFactory(course=course, is_listed=True)
        not_listed_course_run = factories.CourseRunFactory(
            course=course, is_listed=False
        )

        factories.ProductFactory.create_batch(3, courses=[course])
        webhook_mock.reset_mock()

        call_command(
            "synchronize_course_runs",
            course=course.code,
            course_runs=[
                listed_course_run.id,
                not_listed_course_run.id,
                str(uuid.uuid4()),
            ],
        )

        webhook_mock.assert_called_once_with([listed_course_run.get_serialized()])

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_commands_synchronize_course_runs_with_single_course_run_id(
        self, webhook_mock
    ):
        """
        This command should accept a single course run id as argument instead of a list.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(course=course, is_listed=True)

        webhook_mock.reset_mock()

        call_command(
            "synchronize_course_runs", course=course.code, course_run=course_run.id
        )

        webhook_mock.assert_called_once_with([course_run.get_serialized()])

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_commands_synchronize_course_runs_with_products(self, webhook_mock):
        """
        If product ids are provided, the command should synchronize only
        credential products matching ids.
        """
        course = factories.CourseFactory()
        credential_product = factories.ProductFactory(
            courses=[course], type=enums.PRODUCT_TYPE_CREDENTIAL
        )
        certificate_product = factories.ProductFactory(
            courses=[course], type=enums.PRODUCT_TYPE_CERTIFICATE
        )
        enrollment_product = factories.ProductFactory(
            courses=[course], type=enums.PRODUCT_TYPE_ENROLLMENT
        )
        factories.CourseRunFactory.create_batch(3, course=course, is_listed=True)

        webhook_mock.reset_mock()

        call_command(
            "synchronize_course_runs",
            course=course.code,
            products=[
                credential_product.id,
                certificate_product.id,
                enrollment_product.id,
                str(uuid.uuid4()),
            ],
        )

        webhook_mock.assert_called_once_with(
            Product.get_equivalent_serialized_course_runs_for_products(
                [credential_product], courses=[course]
            )
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_commands_synchronize_course_runs_with_single_product_id(
        self, webhook_mock
    ):
        """
        This command should accept a single product id as argument instead of a list.
        """
        course = factories.CourseFactory()
        credential_product = factories.ProductFactory(
            courses=[course], type=enums.PRODUCT_TYPE_CREDENTIAL
        )

        webhook_mock.reset_mock()

        call_command(
            "synchronize_course_runs", course=course.code, product=credential_product.id
        )

        webhook_mock.assert_called_once_with(
            Product.get_equivalent_serialized_course_runs_for_products(
                [credential_product], courses=[course]
            )
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_commands_synchronize_course_runs_with_visibility(self, webhook_mock):
        """
        The command should accept a visibility option to enforce the visibility
        of synchronized resources.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(course=course, is_listed=True)
        factories.CourseRunFactory(course=course, is_listed=False)

        product = factories.ProductFactory(
            courses=[course], type=enums.PRODUCT_TYPE_CREDENTIAL
        )
        factories.ProductFactory(courses=[course], type=enums.PRODUCT_TYPE_CERTIFICATE)
        factories.ProductFactory(courses=[course], type=enums.PRODUCT_TYPE_ENROLLMENT)
        webhook_mock.reset_mock()

        visibility = random.choice(enums.CATALOG_VISIBILITY_CHOICES)
        call_command(
            "synchronize_course_runs", course=course.code, visibility=visibility
        )

        webhook_mock.assert_called_once_with(
            [
                course_run.get_serialized(visibility),
                *Product.get_equivalent_serialized_course_runs_for_products(
                    [product], courses=[course], visibility=visibility
                ),
            ]
        )
