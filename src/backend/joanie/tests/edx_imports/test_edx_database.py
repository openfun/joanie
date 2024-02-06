"""Module for testing the Open edX database class."""
from django.test import TestCase

from joanie.edx_imports.edx_database import OpenEdxDB
from joanie.edx_imports.edx_factories import (
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
