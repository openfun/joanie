"""Module to connect to Open edX database and create models"""
# pylint: disable=too-many-instance-attributes

import logging

from django.conf import settings

from sqlalchemy import URL, create_engine, select
from sqlalchemy.orm import Session, joinedload, load_only
from sqlalchemy.sql.functions import count

from joanie.edx_imports.edx_models import (
    Course,
    CourseOverview,
    University,
)

logger = logging.getLogger(__name__)


class OpenEdxDB:
    """Class to connect to Open edX database and create models"""

    session = None
    University = None
    CourseOverview = None
    User = None
    UserProfile = None
    UserPreference = None
    StudentCourseEnrollment = None

    def __init__(self, engine=None, session=None):
        if engine is not None:
            self.engine = engine
        else:
            url = URL.create(
                drivername="mysql+pymysql",
                username=settings.EDX_DATABASE_USER,
                password=settings.EDX_DATABASE_PASSWORD,
                host=settings.EDX_DATABASE_HOST,
                port=settings.EDX_DATABASE_PORT,
                database=settings.EDX_DATABASE_NAME,
            )
            self.engine = create_engine(url, echo=settings.EDX_DATABASE_DEBUG)
        if session is not None:
            self.session = session
        else:
            self.session = Session(self.engine)

        self.University = University  # pylint: disable=invalid-name
        self.CourseOverview = CourseOverview  # pylint: disable=invalid-name
        self.Course = Course  # pylint: disable=invalid-name

    def get_universities_count(self, offset=0, limit=0):
        """
        Get universities count from Open edX database

        SELECT count(universities_university.id) AS count_1
        FROM universities_university
        """
        query_count = select(count(self.University.id))
        universities_count = self.session.execute(query_count).scalar()
        universities_count -= offset
        if limit:
            return min(universities_count, limit)
        return universities_count

    def get_universities(self, start, stop):
        """
        Get universities from Open edX database

        SELECT universities_university.id,
               universities_university.name,
               universities_university.code,
               universities_university.logo
        FROM universities_university
        """
        query = (
            select(self.University)
            .options(
                load_only(
                    self.University.code,
                    self.University.name,
                    self.University.logo,
                )
            )
            .slice(start, stop)
        )
        return self.session.scalars(query).all()

    def get_course_overviews_count(self, offset=0, limit=0):
        """
        Get course_overviews count from Open edX database

        SELECT count(course_overviews_courseoverview.id) AS count_1
        FROM course_overviews_courseoverview
        """
        query_count = select(count(self.CourseOverview.id)).join(
            self.Course,
            self.CourseOverview.id == self.Course.key,
        )
        course_overviews_count = self.session.execute(query_count).scalar()
        course_overviews_count -= offset
        if limit:
            return min(course_overviews_count, limit)
        return course_overviews_count

    def get_course_overviews(self, start, stop):
        """
        Get course_overviews from Open edX database

        SELECT course_overviews_courseoverview.id,
               course_overviews_courseoverview.created,
               course_overviews_courseoverview.display_name,
               course_overviews_courseoverview.start,
               course_overviews_courseoverview."end",
               course_overviews_courseoverview.enrollment_start,
               course_overviews_courseoverview.enrollment_end,
               courses_course.language, courses_course_1.id AS id_1,
               courses_course_1.language AS language_1
        FROM course_overviews_courseoverview
        JOIN courses_course
             ON course_overviews_courseoverview.id = courses_course.key
        LEFT OUTER JOIN courses_course AS courses_course_1
             ON course_overviews_courseoverview.id = courses_course_1.key
        """
        query = (
            select(self.CourseOverview, self.Course.language)
            .join(
                self.Course,
                self.CourseOverview.id == self.Course.key,
            )
            .options(
                load_only(
                    self.CourseOverview.id,
                    self.CourseOverview.display_name,
                    self.CourseOverview.start,
                    self.CourseOverview.end,
                    self.CourseOverview.enrollment_start,
                    self.CourseOverview.enrollment_end,
                    self.CourseOverview.created,
                ),
                joinedload(self.CourseOverview.course).load_only(
                    self.Course.language,
                ),
            )
            .slice(start, stop)
        )
        return self.session.scalars(query).all()
