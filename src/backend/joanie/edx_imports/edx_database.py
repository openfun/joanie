"""Module to connect to Open edX database and create models"""
# pylint: disable=too-many-instance-attributes

import logging

from django.conf import settings

from sqlalchemy import URL, create_engine, distinct, select
from sqlalchemy.orm import Session, joinedload, load_only
from sqlalchemy.sql.functions import count

from joanie.edx_imports.edx_models import (
    Course,
    CourseEnrollment,
    CourseOverview,
    GeneratedCertificate,
    University,
    User,
    UserPreference,
    UserProfile,
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
            self.engine = create_engine(
                url, echo=settings.EDX_DATABASE_DEBUG, pool_pre_ping=True
            )
        if session is not None:
            self.session = session
        else:
            self.session = Session(self.engine)

        self.University = University  # pylint: disable=invalid-name
        self.CourseOverview = CourseOverview  # pylint: disable=invalid-name
        self.Course = Course  # pylint: disable=invalid-name
        self.User = User  # pylint: disable=invalid-name
        self.UserProfile = UserProfile  # pylint: disable=invalid-name
        self.UserPreference = UserPreference  # pylint: disable=invalid-name
        self.StudentCourseEnrollment = CourseEnrollment  # pylint: disable=invalid-name
        self.Certificate = GeneratedCertificate  # pylint: disable=invalid-name

    def get_universities_count(self, offset=0, limit=0):
        """
        Get universities count from Open edX database

        SELECT count(universities_university.id) AS count_1
        FROM universities_university
        """
        query_count = select(count(self.University.id)).prefix_with(
            "SQL_NO_CACHE", dialect="mysql"
        )
        universities_count = self.session.execute(query_count).scalar()
        universities_count -= offset
        if limit:
            return min(universities_count, limit)
        return universities_count

    def get_universities(self, offset, limit):
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
            .prefix_with("SQL_NO_CACHE", dialect="mysql")
            .options(
                load_only(
                    self.University.code,
                    self.University.name,
                    self.University.logo,
                )
            )
            .offset(offset)
            .limit(limit)
        )
        return self.session.scalars(query).all()

    def get_course_overviews_count(self, offset=0, limit=0):
        """
        Get course_overviews count from Open edX database

        SELECT count(course_overviews_courseoverview.id) AS count_1
        FROM course_overviews_courseoverview
        """
        query_count = (
            select(count(self.CourseOverview.id))
            .prefix_with("SQL_NO_CACHE", dialect="mysql")
            .join(
                self.Course,
                self.CourseOverview.id == self.Course.key,
            )
        )
        course_overviews_count = self.session.execute(query_count).scalar()
        course_overviews_count -= offset
        if limit:
            return min(course_overviews_count, limit)
        return course_overviews_count

    def get_course_overviews(self, offset, limit):
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
            .prefix_with("SQL_NO_CACHE", dialect="mysql")
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
            .offset(offset)
            .limit(limit)
        )
        return self.session.scalars(query).all()

    def get_users_count(self, offset=0, limit=0):
        """
        Get users count from Open edX database

        SELECT count(auth_user.id) AS count_1
        FROM auth_user
                 JOIN auth_userprofile ON auth_user.id = auth_userprofile.user_id
        """
        query_count = (
            select(count(distinct(self.User.id)))
            .prefix_with("SQL_NO_CACHE", dialect="mysql")
            .join(self.UserProfile, self.User.id == self.UserProfile.user_id)
        )
        users_count = self.session.execute(query_count).scalar()
        users_count -= offset
        if limit:
            return min(users_count, limit)
        return users_count

    def get_users(self, offset, limit):
        """
        Get users from Open edX database by slicing

        SELECT auth_user.id,
            auth_user.username,
            auth_user.first_name,
            auth_user.last_name,
            auth_user.email,
            auth_user.password,
            auth_user.is_staff,
            auth_user.is_active,
            auth_user.is_superuser,
            auth_user.date_joined,
            auth_user.last_login,
            auth_userprofile.name,
            auth_userprofile_1.id   AS id_1,
            auth_userprofile_1.name AS name_1
        FROM auth_user
        JOIN auth_userprofile
            ON auth_user.id = auth_userprofile.user_id
        LEFT OUTER JOIN auth_userprofile AS auth_userprofile_1
            ON auth_user.id = auth_userprofile_1.user_id
        LIMIT :param_1 OFFSET :param_2
        """
        query = (
            select(self.User, self.UserProfile.name)
            .prefix_with("SQL_NO_CACHE", dialect="mysql")
            .join(self.UserProfile, self.User.id == self.UserProfile.user_id)
            .options(
                load_only(
                    self.User.id,
                    self.User.username,
                    self.User.password,
                    self.User.email,
                    self.User.first_name,
                    self.User.last_name,
                    self.User.is_active,
                    self.User.is_staff,
                    self.User.is_superuser,
                    self.User.date_joined,
                    self.User.last_login,
                ),
                joinedload(self.User.auth_userprofile).load_only(
                    self.UserProfile.name,
                ),
            )
            .offset(offset)
            .limit(limit)
        )
        return self.session.scalars(query).unique().all()

    def get_enrollments_count(self, offset=0, limit=0, course_id=None):
        """
        Get enrollments count from Open edX database

        SELECT
            count(student_courseenrollment.id) AS count_1
        FROM student_courseenrollment
            JOIN course_overviews_courseoverview
                ON student_courseenrollment.course_id = course_overviews_courseoverview.id
            JOIN auth_user
                ON student_courseenrollment.user_id = auth_user.id
        """
        query_count = (
            select(count(self.StudentCourseEnrollment.id))
            .prefix_with("SQL_NO_CACHE", dialect="mysql")
            .join(
                self.CourseOverview,
                self.StudentCourseEnrollment.course_id == self.CourseOverview.id,
            )
            .join(self.User, self.StudentCourseEnrollment.user_id == self.User.id)
        )
        if course_id:
            query_count = query_count.where(
                self.StudentCourseEnrollment.course_id == course_id
            )
        enrollments_count = self.session.execute(query_count).scalar()
        enrollments_count -= offset
        if limit:
            return min(enrollments_count, limit)
        return enrollments_count

    def get_enrollments(self, offset, limit, course_id=None):
        """
        Get enrollments from Open edX database by slicing

        SELECT student_courseenrollment.id,
               student_courseenrollment.user_id,
               student_courseenrollment.course_id,
               student_courseenrollment.is_active,
               student_courseenrollment.created,
               auth_user.id AS id_1,
               auth_user.username,
               auth_user.first_name,
               auth_user.last_name,
               auth_user.email,
               auth_user.password,
               auth_user.is_staff,
               auth_user.is_active AS is_active_1,
               auth_user.is_superuser,
               auth_user.date_joined,
               auth_user.last_login,
               auth_user_1.id AS id_2,
               auth_user_1.username AS username_1
        FROM student_courseenrollment
        JOIN course_overviews_courseoverview
            ON student_courseenrollment.course_id = course_overviews_courseoverview.id
        JOIN auth_user
            ON student_courseenrollment.user_id = auth_user.id
        LEFT OUTER JOIN auth_user AS auth_user_1
            ON auth_user_1.id = student_courseenrollment.user_id
        LIMIT :param_1
        """
        query = (
            select(self.StudentCourseEnrollment, self.User)
            .prefix_with("SQL_NO_CACHE", dialect="mysql")
            .join(
                self.CourseOverview,
                self.StudentCourseEnrollment.course_id == self.CourseOverview.id,
            )
            .join(self.User, self.StudentCourseEnrollment.user_id == self.User.id)
            .options(
                load_only(
                    self.StudentCourseEnrollment.course_id,
                    self.StudentCourseEnrollment.created,
                    self.StudentCourseEnrollment.is_active,
                    self.StudentCourseEnrollment.user_id,
                ),
                joinedload(self.StudentCourseEnrollment.user).load_only(
                    self.User.username,
                ),
            )
            .offset(offset)
            .limit(limit)
        )
        if course_id:
            query = query.where(self.StudentCourseEnrollment.course_id == course_id)
        return self.session.scalars(query).all()

    def get_certificates_count(self, offset=0, limit=0, course_id=None):
        """
        Get downloadable certificates count from Open edX database

        SELECT count(generated_certificate.id) AS count_1
        FROM generated_certificate
        WHERE generated_certificate.status = "downloadable"
        """
        query_count = (
            select(count(self.Certificate.id))
            .prefix_with("SQL_NO_CACHE", dialect="mysql")
            .where(self.Certificate.status == "downloadable")
        )
        if course_id:
            query_count = query_count.where(self.Certificate.course_id == course_id)
        certificates_count = self.session.execute(query_count).scalar()
        certificates_count -= offset
        if limit:
            return min(certificates_count, limit)
        return certificates_count

    def get_certificates(self, offset, limit, course_id=None):
        """
        Get downloadable certificates from Open edX database by slicing

        SELECT generated_certificate.id,
                generated_certificate.user_id,
                generated_certificate.course_id,
                generated_certificate.created_date,
                generated_certificate.mode
        FROM generated_certificate
        WHERE generated_certificate.status = "downloadable"
        LIMIT :param_1
        OFFSET :param_2
        """
        query = (
            select(self.Certificate)
            .prefix_with("SQL_NO_CACHE", dialect="mysql")
            .options(
                load_only(
                    self.Certificate.id,
                    self.Certificate.user_id,
                    self.Certificate.course_id,
                    self.Certificate.created_date,
                    self.Certificate.mode,
                )
            )
            .where(self.Certificate.status == "downloadable")
            .offset(offset)
            .limit(limit)
        )
        if course_id:
            query = query.where(self.Certificate.course_id == course_id)
        return self.session.scalars(query).all()
