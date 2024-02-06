"""Module for testing the Open edX database class."""
from django.test import TestCase

from joanie.edx_imports.edx_database import OpenEdxDB
from joanie.edx_imports.edx_factories import (
    EdxCourseOverviewFactory,
    EdxUniversityFactory,
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

        universities = self.db.get_universities(start=0, stop=9)

        self.assertEqual(len(universities), 3)
        self.assertEqual(len(edx_universities), 3)
        self.assertCountEqual(universities, edx_universities)

    def test_edx_database_get_universities_empty(self):
        """Test the get_universities method when there are no universities."""
        universities = self.db.get_universities(start=0, stop=9)

        self.assertEqual(universities, [])

    def test_edx_database_get_course_overviews(self):
        """Test the get_course_overviews method."""
        edx_course_overviews = EdxCourseOverviewFactory.create_batch(3)

        course_overviews = self.db.get_course_overviews(start=0, stop=9)

        self.assertEqual(len(course_overviews), 3)
        self.assertEqual(len(edx_course_overviews), 3)
        self.assertCountEqual(course_overviews, edx_course_overviews)

    def test_edx_database_get_course_overviews_empty(self):
        """Test the get_course_overviews method when there are no course_overviews."""
        course_overviews = self.db.get_course_overviews(start=0, stop=9)

        self.assertEqual(course_overviews, [])
