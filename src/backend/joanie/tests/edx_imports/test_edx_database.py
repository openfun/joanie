# pylint: disable=too-many-public-methods
"""Module for testing the Open edX database class."""

from django.test import TestCase

from joanie.edx_imports.edx_database import OpenEdxDB
from joanie.edx_imports.edx_factories import (
    EdxCourseOverviewFactory,
    EdxEnrollmentFactory,
    EdxGeneratedCertificateFactory,
    EdxUniversityFactory,
    EdxUserFactory,
    engine,
    session,
)
from joanie.edx_imports.edx_models import Base


class OpenEdxDBTestCase(TestCase):
    """Test case for the Open edX database class."""

    maxDiff = None

    def setUp(self):
        """Set up the test case."""
        self.db = OpenEdxDB(engine, session)
        Base.metadata.create_all(engine)

    def tearDown(self):
        """Tear down the test case."""
        self.db.session.rollback()

    def test_edx_database_get_universities(self):
        """Test the get_universities method."""
        edx_universities = EdxUniversityFactory.create_batch(3)

        universities = self.db.get_universities(offset=0, limit=9)

        self.assertEqual(len(universities), 3)
        self.assertEqual(len(edx_universities), 3)
        self.assertCountEqual(universities, edx_universities)

    def test_edx_database_get_universities_empty(self):
        """Test the get_universities method when there are no universities."""
        universities = self.db.get_universities(offset=0, limit=9)

        self.assertEqual(universities, [])

    def test_edx_database_get_course_overviews_count(self):
        """Test the get_course_overviews method."""
        EdxCourseOverviewFactory.create_batch(3)

        course_overviews_count = self.db.get_course_overviews_count()

        self.assertEqual(course_overviews_count, 3)

    def test_edx_database_get_course_overviews_count_offset_limit(self):
        """Test the get_course_overviews method."""
        EdxCourseOverviewFactory.create_batch(100)

        course_overviews_count = self.db.get_course_overviews_count(offset=10, limit=30)

        self.assertEqual(course_overviews_count, 30)

    def test_edx_database_get_course_overviews(self):
        """Test the get_course_overviews method."""
        edx_course_overviews = EdxCourseOverviewFactory.create_batch(3)

        course_overviews = self.db.get_course_overviews(offset=0, limit=9)

        self.assertEqual(len(course_overviews), 3)
        self.assertEqual(len(edx_course_overviews), 3)
        self.assertCountEqual(course_overviews, edx_course_overviews)

    def test_edx_database_get_course_overviews_empty(self):
        """Test the get_course_overviews method when there are no course_overviews."""
        course_overviews = self.db.get_course_overviews(offset=0, limit=9)

        self.assertEqual(course_overviews, [])

    def test_edx_database_get_course_overviews_offset_limit(self):
        """Test the get_course_overviews method."""
        edx_course_overviews = EdxCourseOverviewFactory.create_batch(100)

        course_overviews = self.db.get_course_overviews(offset=10, limit=3)

        self.assertEqual(len(course_overviews), 3)
        self.assertEqual(len(edx_course_overviews), 100)
        self.assertCountEqual(
            course_overviews,
            sorted(edx_course_overviews, key=lambda course: course.id)[10:13],
        )

    def test_edx_database_get_users_count(self):
        """Test the get_users_count method."""
        EdxUserFactory.create_batch(3)
        # User with no profile should not be included
        EdxUserFactory(auth_userprofile=None)
        # User with no preference should be included
        EdxUserFactory(user_api_userpreference=None)

        users_count = self.db.get_users_count()

        self.assertEqual(users_count, 4)

    def test_edx_database_get_users_count_empty(self):
        """Test the get_users_count method when there are no users."""
        users_count = self.db.get_users_count()

        self.assertEqual(users_count, 0)

    def test_edx_database_get_users_count_offset(self):
        """Test the get_users_count method with an offset."""
        EdxUserFactory.create_batch(10)

        users_count = self.db.get_users_count(offset=1)

        self.assertEqual(users_count, 9)

    def test_edx_database_get_users_count_limit(self):
        """Test the get_users_count method with a limit."""
        EdxUserFactory.create_batch(10)

        users_count = self.db.get_users_count(limit=5)

        self.assertEqual(users_count, 5)

    def test_edx_database_get_users_count_offset_limit(self):
        """Test the get_users_count method with an offset and a limit."""
        EdxUserFactory.create_batch(10)

        users_count = self.db.get_users_count(offset=8, limit=5)

        self.assertEqual(users_count, 2)

    def test_edx_database_get_users(self):
        """Test the get_users method."""
        edx_users = EdxUserFactory.create_batch(3)
        # User with no profile should not be included
        EdxUserFactory(auth_userprofile=None)
        # User with no preference should be included
        edx_user_no_preference = EdxUserFactory(user_api_userpreference=None)
        edx_users.append(edx_user_no_preference)

        users = self.db.get_users(start=0, stop=9)

        self.assertEqual(len(edx_users), 4, "Expected 4 edx_users")
        self.assertEqual(len(users), 4, "Expected 4 users")
        self.assertCountEqual(users, edx_users, "Expected the same users")

    def test_edx_database_get_users_empty(self):
        """Test the get_users method when there are no users."""
        users = self.db.get_users(start=0, stop=9)

        self.assertEqual(users, [])

    def test_edx_database_get_users_slice(self):
        """Test the get_users method with a slice."""
        edx_users = EdxUserFactory.create_batch(3)

        users = self.db.get_users(start=0, stop=2)

        self.assertEqual(len(users), 2)
        self.assertEqual(len(edx_users), 3)
        self.assertCountEqual(users, edx_users[:2])

    def test_edx_database_get_users_slice_empty(self):
        """Test the get_users method with a slice when there are no users."""
        EdxUserFactory.create_batch(3)

        users = self.db.get_users(start=3, stop=9)

        self.assertEqual(users, [])

    def test_edx_database_get_enrollments_count(self):
        """Test the get_enrollments_count method."""
        edx_course_overviews = EdxCourseOverviewFactory.create_batch(3)
        for edx_course_overview in edx_course_overviews:
            EdxEnrollmentFactory(course_id=edx_course_overview.id)

        enrollments_count = self.db.get_enrollments_count()

        self.assertEqual(enrollments_count, 3)

    def test_edx_database_get_enrollments_count_offset_limit(self):
        """Test the get_enrollments_count method."""
        edx_course_overviews = EdxCourseOverviewFactory.create_batch(100)
        for edx_course_overview in edx_course_overviews:
            EdxEnrollmentFactory(course_id=edx_course_overview.id)

        enrollments_count = self.db.get_enrollments_count(offset=20, limit=10)

        self.assertEqual(enrollments_count, 10)

    def test_edx_database_get_enrollments_count_empty(self):
        """Test the get_enrollments_count method when there are no enrollments."""
        enrollments_count = self.db.get_enrollments_count()

        self.assertEqual(enrollments_count, 0)

    def test_edx_database_get_enrollments(self):
        """Test the get_enrollments method."""
        edx_course_overviews = EdxCourseOverviewFactory.create_batch(3)
        edx_users = EdxUserFactory.create_batch(3)
        for edx_course_overview in edx_course_overviews:
            for edx_user in edx_users:
                EdxEnrollmentFactory(
                    course_id=edx_course_overview.id, user_id=edx_user.id, user=edx_user
                )
        enrollments = self.db.get_enrollments(start=0, stop=9)

        self.assertEqual(len(enrollments), 9)

    def test_edx_database_get_enrollments_offset_limit(self):
        """Test the get_enrollments method."""
        edx_course_overviews = EdxCourseOverviewFactory.create_batch(100)
        edx_users = EdxUserFactory.create_batch(3)
        for edx_course_overview in edx_course_overviews:
            for edx_user in edx_users:
                EdxEnrollmentFactory(
                    course_id=edx_course_overview.id, user_id=edx_user.id, user=edx_user
                )
        enrollments = self.db.get_enrollments(start=20, stop=10)

        self.assertEqual(len(enrollments), len(edx_course_overviews[20:30]))

    def test_edx_database_get_certificates_count(self):
        """Test the get_certificates_count method."""
        EdxGeneratedCertificateFactory.create_batch(3, status="notpassing")
        EdxGeneratedCertificateFactory.create_batch(3, status="downloadable")
        EdxGeneratedCertificateFactory.create_batch(3, status="unavailable")

        certificates_count = self.db.get_certificates_count()

        self.assertEqual(certificates_count, 3)

    def test_edx_database_get_certificates(self):
        """Test the get_certificates method."""
        EdxGeneratedCertificateFactory.create_batch(3, status="notpassing")
        edx_certificates_downloadable = EdxGeneratedCertificateFactory.create_batch(
            3, status="downloadable"
        )
        EdxGeneratedCertificateFactory.create_batch(3, status="unavailable")

        certificates = self.db.get_certificates(start=0, stop=9)

        self.assertEqual(len(certificates), 3)
        self.assertEqual(len(edx_certificates_downloadable), 3)
        self.assertCountEqual(certificates, edx_certificates_downloadable)
