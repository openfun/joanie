from unittest.mock import patch, MagicMock

from django.test import TestCase

from joanie.lms_handler.edx_imports.edx_database import OpenEdxDB, DEBUG, EDX_DATABASE_URL


class OpenEdxDBTestCase(TestCase):
    def setUp(self):
        self.db = OpenEdxDB()

    @patch('joanie.lms_handler.edx_imports.edx_database.create_engine')
    @patch('joanie.lms_handler.edx_imports.edx_database.automap_base')
    @patch('joanie.lms_handler.edx_imports.edx_database.Session')
    def test_edx_database_connect_to_edx_db(self, mock_session, mock_base, mock_create_engine):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        mock_base_instance = MagicMock()
        mock_base.return_value = mock_base_instance

        self.db.connect_to_edx_db()

        mock_create_engine.assert_called_once_with(EDX_DATABASE_URL, echo=DEBUG)
        mock_base_instance.prepare.assert_called_once()
        mock_session.assert_called_once_with(mock_engine)
        self.assertEqual(self.db.University, mock_base_instance.classes.universities_university)
        self.assertEqual(self.db.CourseOverview, mock_base_instance.classes.course_overviews_courseoverview)
        self.assertEqual(self.db.User, mock_base_instance.classes.auth_user)
        self.assertEqual(self.db.StudentCourseEnrollment, mock_base_instance.classes.student_courseenrollment)

    @patch('joanie.lms_handler.edx_imports.edx_database.connect_to_edx_db')
    @patch('joanie.lms_handler.edx_imports.edx_database.Session')
    @patch('joanie.lms_handler.edx_imports.edx_database.select')
    def test_edx_database_get_universities(self, mock_select, mock_session, mock_connect):
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        mock_select_instance = MagicMock()
        mock_select.return_value = mock_select_instance

        mock_scalars = MagicMock()
        mock_session_instance.scalars.return_value = mock_scalars

        mock

        universities = self.db.get_universities()

        mock_select.assert_called_once_with(self.db.University)
        mock_session_instance.scalars.assert_called_once_with(mock_select_instance)
        mock_scalars.all.assert_called_once()

        self.assertEqual(universities, mock_scalars.all.return_value)
        breakpoint()