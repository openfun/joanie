"""Test suite for the management command `synchronize_course_runs`."""
from os.path import dirname, join, realpath
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import TestCase, override_settings

import factory
import responses

from joanie.core import factories, models, utils
from joanie.lms_handler.api import detect_lms_from_resource_link
from joanie.lms_handler.backends.openedx import split_course_key
from joanie.lms_handler.edx_imports import edx_factories
from joanie.lms_handler.management.commands.migrate_edx import (
    EDX_DOMAIN,
    extract_course_number,
    make_date_aware,
)

LOGO_NAME = "creative_common.jpeg"
with open(join(dirname(realpath(__file__)), f"images/{LOGO_NAME}"), "rb") as logo:
    LOGO_CONTENT = logo.read()


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
    },
    JOANIE_LMS_BACKENDS=[
        {
            "BASE_URL": "http://localhost:8073",
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            "JS_BACKEND": "base",
            "JS_COURSE_REGEX": r"^.*/courses/(?<course_id>.*)/course/?$",
        }
    ],
    TIME_ZONE="UTC",
)
class MigrateOpenEdxTestCase(TestCase):
    """Test case for the management command `migrate_edx`."""

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_universities"
    )
    @responses.activate(assert_all_requests_are_fired=True)
    def test_import_universities_create(self, mock_get_universities):
        """
        Test that universities are created from the edx universities and that their
        logos are downloaded.
        """
        edx_universities = edx_factories.EdxUniversityFactory.create_batch(10)
        mock_get_universities.return_value = edx_universities

        for edx_university in edx_universities:
            responses.add(
                responses.GET,
                f"https://{EDX_DOMAIN}/media/{edx_university.logo}",
                body=LOGO_CONTENT,
            )

        call_command("migrate_edx", "--universities")

        self.assertEqual(models.Organization.objects.count(), len(edx_universities))
        for edx_university in edx_universities:
            organization = models.Organization.objects.get(
                code=utils.normalize_code(edx_university.code)
            )
            self.assertEqual(organization.title, edx_university.name)
            self.assertEqual(organization.logo.name, edx_university.logo)
            self.assertIsNotNone(organization.logo.read())
            self.assertTrue(default_storage.exists(organization.logo.name))

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_universities"
    )
    @responses.activate(assert_all_requests_are_fired=True)
    def test_import_universities_update(self, mock_get_universities):
        """
        Test that universities are updated from the edx universities and that their
        logos are downloaded.
        """
        organization = factories.OrganizationFactory.create(
            code="orga",
            title="Organization 1 old title",
            logo=None,
        )
        edx_universities = [
            edx_factories.EdxUniversityFactory.create(
                code=organization.code,
                name="Organization 1",
                logo="logo.png",
            )
        ]
        mock_get_universities.return_value = edx_universities

        for edx_university in edx_universities:
            responses.add(
                responses.GET,
                f"https://{EDX_DOMAIN}/media/{edx_university.logo}",
                body=LOGO_CONTENT,
            )

        call_command("migrate_edx", "--universities")

        self.assertEqual(models.Organization.objects.count(), len(edx_universities))
        for edx_university in edx_universities:
            organization = models.Organization.objects.get(
                code=utils.normalize_code(edx_university.code)
            )
            self.assertEqual(organization.title, edx_university.name)
            self.assertEqual(organization.logo.name, edx_university.logo)
            self.assertIsNotNone(organization.logo.read())
            self.assertTrue(default_storage.exists(organization.logo.name))

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_course_overviews"
    )
    def test_import_course_runs_create(self, mock_get_course_overviews):
        """
        Test that course runs are created from the edx course overviews.
        """
        edx_course_overviews = edx_factories.EdxCourseOverviewFactory.create_batch(10)
        mock_get_course_overviews.return_value = edx_course_overviews

        call_command("migrate_edx", "--course-runs")

        self.assertEqual(models.Course.objects.count(), len(edx_course_overviews))
        self.assertEqual(models.CourseRun.objects.count(), len(edx_course_overviews))
        for edx_course_overview in edx_course_overviews:
            course = models.Course.objects.get(
                code=extract_course_number(edx_course_overview.id)
            )
            self.assertEqual(course.title, edx_course_overview.display_name)
            self.assertEqual(
                course.created_on, make_date_aware(edx_course_overview.created)
            )
            course_run = models.CourseRun.objects.get(
                course=course,
            )
            course_run.set_current_language("fr")
            self.assertEqual(course_run.title, edx_course_overview.display_name)
            self.assertEqual(
                course_run.start, make_date_aware(edx_course_overview.start)
            )
            self.assertEqual(course_run.end, make_date_aware(edx_course_overview.end))
            self.assertEqual(
                course_run.enrollment_start,
                make_date_aware(edx_course_overview.enrollment_start),
            )
            self.assertEqual(
                course_run.enrollment_end,
                make_date_aware(edx_course_overview.enrollment_end),
            )
            self.assertEqual(course_run.languages, ["fr"])

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_course_overviews"
    )
    def test_import_course_create_unknown_course_with_title(
        self, mock_get_course_overviews
    ):
        """
        Test that course runs are created from the edx course overviews and that the
        course is created if it does not exist.
        """
        edx_course_overviews = [
            edx_factories.EdxCourseOverviewFactory.create(
                id="course-v1:edX+DemoX+01",
                display_name="my course run",
            )
        ]
        mock_get_course_overviews.return_value = edx_course_overviews

        call_command("migrate_edx", "--course-runs")

        self.assertEqual(models.CourseRun.objects.count(), len(edx_course_overviews))
        for edx_course_overview in edx_course_overviews:
            course = models.Course.objects.get(
                code=extract_course_number(edx_course_overview.id)
            )
            self.assertEqual(course.title, edx_course_overview.display_name)
            self.assertEqual(
                course.created_on, make_date_aware(edx_course_overview.created)
            )
            course_run = models.CourseRun.objects.get(
                course=course,
            )
            course_run.set_current_language("fr")
            self.assertEqual(course_run.title, edx_course_overview.display_name)
            self.assertEqual(
                course_run.start, make_date_aware(edx_course_overview.start)
            )
            self.assertEqual(course_run.end, make_date_aware(edx_course_overview.end))
            self.assertEqual(
                course_run.enrollment_start,
                make_date_aware(edx_course_overview.enrollment_start),
            )
            self.assertEqual(
                course_run.enrollment_end,
                make_date_aware(edx_course_overview.enrollment_end),
            )
            self.assertEqual(course_run.languages, ["fr"])

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_course_overviews"
    )
    def test_import_course_create_unknown_course_no_title(
        self, mock_get_course_overviews
    ):
        """
        Test that course runs are created from the edx course overviews and that the
        course is created if it does not exist.
        When the course overview has no title, the course title is set to the course
        code.
        """
        edx_course_overviews = [
            edx_factories.EdxCourseOverviewFactory.create(
                id="course-v1:edX+DemoX+01",
                display_name=None,
            )
        ]
        mock_get_course_overviews.return_value = edx_course_overviews

        call_command("migrate_edx", "--course-runs")

        self.assertEqual(models.CourseRun.objects.count(), len(edx_course_overviews))
        for edx_course_overview in edx_course_overviews:
            course = models.Course.objects.get(
                code=extract_course_number(edx_course_overview.id)
            )
            self.assertEqual(course.title, course.code)
            self.assertEqual(
                course.created_on, make_date_aware(edx_course_overview.created)
            )
            course_run = models.CourseRun.objects.get(
                course=course,
            )
            course_run.set_current_language("fr")
            self.assertEqual(
                course_run.start, make_date_aware(edx_course_overview.start)
            )
            self.assertEqual(course_run.end, make_date_aware(edx_course_overview.end))
            self.assertEqual(
                course_run.enrollment_start,
                make_date_aware(edx_course_overview.enrollment_start),
            )
            self.assertEqual(
                course_run.enrollment_end,
                make_date_aware(edx_course_overview.enrollment_end),
            )
            self.assertEqual(course_run.languages, ["fr"])

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_course_overviews"
    )
    def test_import_course_runs_create_same_course(self, mock_get_course_overviews):
        """
        Test that course runs are created from the edx course overviews and that the
        course is created if it does not exist.
        According to the edx course overview id, only one course is created.
        """
        edx_course_overviews = edx_factories.EdxCourseOverviewFactory.create_batch(
            10, id=factory.Sequence(lambda n: f"course-v1:edX+DemoX+{n}")
        )
        mock_get_course_overviews.return_value = edx_course_overviews

        call_command("migrate_edx", "--course-runs")

        self.assertEqual(models.Course.objects.count(), 1)
        self.assertEqual(models.CourseRun.objects.count(), len(edx_course_overviews))
        course = models.Course.objects.get()
        self.assertEqual(course.title, edx_course_overviews[0].display_name)
        self.assertEqual(
            course.created_on, make_date_aware(edx_course_overviews[0].created)
        )

        course_runs = models.CourseRun.objects.filter(course=course).order_by(
            "updated_on"
        )
        for edx_course_overview, course_run in zip(
            edx_course_overviews, course_runs, strict=False
        ):
            course_run.set_current_language("fr")
            self.assertEqual(course_run.title, edx_course_overview.display_name)
            self.assertEqual(
                course_run.start, make_date_aware(edx_course_overview.start)
            )
            self.assertEqual(course_run.end, make_date_aware(edx_course_overview.end))
            self.assertEqual(
                course_run.enrollment_start,
                make_date_aware(edx_course_overview.enrollment_start),
            )
            self.assertEqual(
                course_run.enrollment_end,
                make_date_aware(edx_course_overview.enrollment_end),
            )
            self.assertEqual(course_run.languages, ["fr"])

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_course_overviews"
    )
    def test_import_course_runs_create_known_course(self, mock_get_course_overviews):
        """
        Test that course runs are created from the edx course overviews and that the
        course is updated as it already exists.
        """
        course = factories.CourseFactory(code="DemoX")
        edx_course_overviews = edx_factories.EdxCourseOverviewFactory.create_batch(
            10, id=factory.Sequence(lambda n: f"course-v1:edX+{course.code}+{n}")
        )
        mock_get_course_overviews.return_value = edx_course_overviews

        call_command("migrate_edx", "--course-runs")

        self.assertEqual(models.Course.objects.count(), 1)
        self.assertEqual(models.CourseRun.objects.count(), len(edx_course_overviews))
        course = models.Course.objects.get()
        self.assertNotEqual(course.title, edx_course_overviews[0].display_name)
        self.assertNotEqual(
            course.created_on, make_date_aware(edx_course_overviews[0].created)
        )

        course_runs = models.CourseRun.objects.filter(course=course).order_by(
            "updated_on"
        )
        for edx_course_overview, course_run in zip(
            edx_course_overviews, course_runs, strict=False
        ):
            course_run.set_current_language("fr")
            self.assertEqual(course_run.title, edx_course_overview.display_name)
            self.assertEqual(
                course_run.start, make_date_aware(edx_course_overview.start)
            )
            self.assertEqual(course_run.end, make_date_aware(edx_course_overview.end))
            self.assertEqual(
                course_run.enrollment_start,
                make_date_aware(edx_course_overview.enrollment_start),
            )
            self.assertEqual(
                course_run.enrollment_end,
                make_date_aware(edx_course_overview.enrollment_end),
            )
            self.assertEqual(course_run.languages, ["fr"])

    @patch("joanie.lms_handler.management.commands.migrate_edx.Command.get_users_count")
    @patch("joanie.lms_handler.management.commands.migrate_edx.Command.get_users")
    def test_import_users_create(self, mock_get_users, mock_get_users_count):
        """
        Test that users are created from the edx users.
        """
        edx_users = edx_factories.EdxUserFactory.create_batch(10)
        mock_get_users.return_value = edx_users
        mock_get_users_count.return_value = len(edx_users)

        call_command("migrate_edx", "--users")

        self.assertEqual(models.User.objects.count(), len(edx_users))
        for edx_user in edx_users:
            user = models.User.objects.get(username=edx_user.username)
            self.assertEqual(user.email, edx_user.email)
            self.assertEqual(user.password, edx_user.password)
            self.assertEqual(user.first_name, edx_user.first_name)
            self.assertEqual(user.last_name, edx_user.last_name)
            self.assertEqual(user.is_active, edx_user.is_active)
            self.assertEqual(user.is_staff, edx_user.is_staff)
            self.assertEqual(user.is_superuser, edx_user.is_superuser)
            self.assertEqual(user.date_joined, make_date_aware(edx_user.date_joined))
            self.assertEqual(user.last_login, make_date_aware(edx_user.last_login))

    @patch("joanie.lms_handler.management.commands.migrate_edx.Command.get_users_count")
    @patch("joanie.lms_handler.management.commands.migrate_edx.Command.get_users")
    def test_import_users_update(self, mock_get_users, mock_get_users_count):
        """
        Test that users are updated from the edx users.
        """
        users = factories.UserFactory.create_batch(10)
        admin = factories.UserFactory.create(username="admin")
        edx_users = [
            edx_factories.EdxUserFactory.create(
                username=user.username,
            )
            for user in users
        ]
        edx_users.append(
            edx_factories.EdxUserFactory.create(
                username=admin.username,
            )
        )

        mock_get_users.return_value = edx_users
        mock_get_users_count.return_value = len(edx_users)

        call_command("migrate_edx", "--users")

        self.assertEqual(models.User.objects.count(), len(edx_users))
        for edx_user in edx_users:
            user = models.User.objects.get(username=edx_user.username)
            if user.username == "admin":
                self.assertEqual(user.email, admin.email)
                self.assertEqual(user.password, admin.password)
                self.assertEqual(user.first_name, admin.first_name)
                self.assertEqual(user.last_name, admin.last_name)
                self.assertEqual(user.is_active, admin.is_active)
                self.assertEqual(user.is_staff, admin.is_staff)
                self.assertEqual(user.is_superuser, admin.is_superuser)
                self.assertEqual(user.date_joined, admin.date_joined)
                self.assertEqual(user.last_login, admin.last_login)
            else:
                self.assertEqual(user.email, edx_user.email)
                self.assertEqual(user.password, edx_user.password)
                self.assertEqual(user.first_name, edx_user.first_name)
                self.assertEqual(user.last_name, edx_user.last_name)
                self.assertEqual(user.is_active, edx_user.is_active)
                self.assertEqual(user.is_staff, edx_user.is_staff)
                self.assertEqual(user.is_superuser, edx_user.is_superuser)
                self.assertEqual(
                    user.date_joined, make_date_aware(edx_user.date_joined)
                )
                self.assertEqual(user.last_login, make_date_aware(edx_user.last_login))

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_enrollments_count"
    )
    @patch("joanie.lms_handler.management.commands.migrate_edx.Command.get_enrollments")
    def test_import_enrollments_create(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that enrollments are created from the edx enrollments.
        """
        edx_enrollments = edx_factories.EdxEnrollmentFactory.create_batch(10)
        for edx_enrollment in edx_enrollments:
            factories.CourseRunFactory.create(
                course__code=extract_course_number(edx_enrollment.course_id)
            )
            factories.UserFactory.create(username=edx_enrollment.auth_user.username)
        mock_get_enrollments.return_value = edx_enrollments
        mock_get_enrollments_count.return_value = len(edx_enrollments)

        call_command("migrate_edx", "--enrollments")

        self.assertEqual(models.Enrollment.objects.count(), len(edx_enrollments))
        for edx_enrollment in edx_enrollments:
            enrollment = models.Enrollment.objects.get(
                user__username=edx_enrollment.auth_user.username,
                course_run__course__code=extract_course_number(
                    edx_enrollment.course_id
                ),
            )
            self.assertEqual(enrollment.is_active, edx_enrollment.is_active)
            self.assertEqual(
                enrollment.created_on, make_date_aware(edx_enrollment.created)
            )
            self.assertEqual(
                enrollment.user.username, edx_enrollment.auth_user.username
            )
            self.assertEqual(
                enrollment.course_run.course.code,
                extract_course_number(edx_enrollment.course_id),
            )

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_enrollments_count"
    )
    @patch("joanie.lms_handler.management.commands.migrate_edx.Command.get_enrollments")
    def test_import_enrollments_update(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that enrollments are updated from the edx enrollments.
        """
        enrollments = factories.EnrollmentFactory.create_batch(1)
        lms = detect_lms_from_resource_link(enrollments[0].course_run.resource_link)
        edx_enrollments = [
            edx_factories.EdxEnrollmentFactory.create(
                auth_user=enrollment.user,
                course_id=lms.extract_course_id(enrollment.course_run.resource_link),
            )
            for enrollment in enrollments
        ]
        mock_get_enrollments.return_value = edx_enrollments
        mock_get_enrollments_count.return_value = len(edx_enrollments)

        call_command("migrate_edx", "--enrollments")

        self.assertEqual(models.Enrollment.objects.count(), len(edx_enrollments))
        for edx_enrollment in edx_enrollments:
            enrollment = models.Enrollment.objects.get(
                user__username=edx_enrollment.auth_user.username,
                course_run__course__code=extract_course_number(
                    edx_enrollment.course_id
                ),
            )
            self.assertEqual(enrollment.is_active, edx_enrollment.is_active)
            self.assertEqual(
                enrollment.created_on, make_date_aware(edx_enrollment.created)
            )
            self.assertEqual(
                enrollment.user.username, edx_enrollment.auth_user.username
            )
            self.assertEqual(
                enrollment.course_run.course.code,
                extract_course_number(edx_enrollment.course_id),
            )

    @patch(
        "joanie.lms_handler.management.commands.migrate_edx.Command.get_enrollments_count"
    )
    @patch("joanie.lms_handler.management.commands.migrate_edx.Command.get_enrollments")
    def test_import_enrollments_create_missing_course_run(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that enrollments are created from the edx enrollments if the course run
        exists.
        """
        edx_enrollments = edx_factories.EdxEnrollmentFactory.create_batch(10)
        i = 0
        for edx_enrollment in edx_enrollments:
            if i % 2 == 0:
                factories.CourseRunFactory.create(
                    course__code=extract_course_number(edx_enrollment.course_id)
                )
            factories.UserFactory.create(username=edx_enrollment.auth_user.username)
            i += 1
        mock_get_enrollments.return_value = edx_enrollments
        mock_get_enrollments_count.return_value = len(edx_enrollments)

        call_command("migrate_edx", "--enrollments")

        self.assertEqual(models.Enrollment.objects.count(), len(edx_enrollments) // 2)
        i = 0
        for edx_enrollment in edx_enrollments:
            if i % 2 == 0:
                continue
            enrollment = models.Enrollment.objects.get(
                user__username=edx_enrollment.auth_user.username,
                course_run__course__code=extract_course_number(
                    edx_enrollment.course_id
                ),
            )
            self.assertEqual(enrollment.is_active, edx_enrollment.is_active)
            self.assertEqual(
                enrollment.created_on, make_date_aware(edx_enrollment.created)
            )
            self.assertEqual(
                enrollment.user.username, edx_enrollment.auth_user.username
            )
            self.assertEqual(
                enrollment.course_run.course.code,
                extract_course_number(edx_enrollment.course_id),
            )
            i += 1
