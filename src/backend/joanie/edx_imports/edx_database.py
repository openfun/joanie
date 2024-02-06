"""Module to connect to Open edX database and create models"""
# pylint: disable=too-many-instance-attributes

import logging

from django.conf import settings

from sqlalchemy import URL, create_engine, select
from sqlalchemy.orm import Session, load_only
from sqlalchemy.sql.functions import count

from joanie.edx_imports.edx_models import University

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
