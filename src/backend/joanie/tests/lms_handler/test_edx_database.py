"""Module for testing the OpenEdxDB class."""
from django.test import TestCase

from joanie.lms_handler.edx_imports.edx_database import OpenEdxDB
from joanie.lms_handler.edx_imports.edx_factories import engine, session, EdxUniversityFactory
from joanie.lms_handler.edx_imports.edx_models import Base


class OpenEdxDBTestCase(TestCase):
    """Test case for the OpenEdxDB class."""
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

        universities = self.db.get_universities()

        for edx_university in edx_universities:
            self.assertIn(edx_university, universities)

    def test_edx_database_get_universities_empty(self):
        """Test the get_universities method when there are no universities."""
        universities = self.db.get_universities()

        self.assertEqual(universities, [])
