"""Module to connect to OpenEdxDb and create models"""
import logging

from sqlalchemy import create_engine, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session, joinedload, load_only
from sqlalchemy.sql.functions import count

logging.StreamHandler.terminator = ""
logger = logging.getLogger(__name__)

# TODO: use env variables and django settings
## Preprod
# DATABASE_HOST = "10.1.2.110"
## Preprod RO

EDX_DOMAIN = "lms.preprod-fun.apps.openfun.fr"
EDX_DATABASE_HOST = "10.1.2.109"
EDX_DATABASE_NAME = "edxapp"
EDX_DATABASE_USER = "edx"
EDX_DATABASE_PASSWORD = "edx_password"  # noqa: S105
EDX_DATABASE_PORT = "3306"
EDX_DATABASE_URL = (
    f"mysql+pymysql://{EDX_DATABASE_USER}:{EDX_DATABASE_PASSWORD}@"
    f"{EDX_DATABASE_HOST}:{EDX_DATABASE_PORT}/{EDX_DATABASE_NAME}"
)
EDX_TIME_ZONE = "UTC"
DEBUG = False


class OpenEdxDB:
    """Class to connect to OpenEdxDb and create models"""

    session = None
    University = None
    CourseOverview = None
    User = None
    StudentCourseEnrollment = None

    def connect_to_edx_db(self):
        """Connect to OpenEdxDb and create models"""
        logger.info("Connecting to OpenEdxDb ")
        engine = create_engine(EDX_DATABASE_URL, echo=DEBUG)
        Base = automap_base()  # pylint: disable=invalid-name
        Base.prepare(
            engine,
            reflect=True,
            reflection_options={
                "only": [
                    "auth_user",
                    "universities_university",
                    "course_overviews_courseoverview",
                    "student_courseenrollment",
                ]
            },
        )
        self.session = Session(engine)
        self.University = Base.classes.universities_university  # pylint: disable=invalid-name
        self.CourseOverview = Base.classes.course_overviews_courseoverview  # pylint: disable=invalid-name
        self.User = Base.classes.auth_user  # pylint: disable=invalid-name
        self.StudentCourseEnrollment = Base.classes.student_courseenrollment  # pylint: disable=invalid-name
        logger.info("Connected\n")

    def get_universities(self):
        """Get universities from OpenEdxDb"""
        if not self.session:
            self.connect_to_edx_db()
        return self.session.scalars(
            select(self.University).options(
                load_only(
                    self.University.code,
                    self.University.name,
                    self.University.logo,
                )
            )
        ).all()

    def get_course_overviews(self):
        """Get course_overviews from OpenEdxDb"""
        if not self.session:
            self.connect_to_edx_db()
        return self.session.scalars(
            select(self.CourseOverview).options(
                load_only(
                    self.CourseOverview.id,
                    self.CourseOverview.display_name,
                    self.CourseOverview.start,
                    self.CourseOverview.end,
                    self.CourseOverview.enrollment_start,
                    self.CourseOverview.enrollment_end,
                    self.CourseOverview.created,
                )
            )
        ).all()

    def get_users_count(self):
        """Get users count from OpenEdxDb"""
        if not self.session:
            self.connect_to_edx_db()
        query_count = select(count(self.User.id))
        return self.session.execute(query_count).scalar()

    def get_users(self, start, stop):
        """Get users from OpenEdxDb by slicing"""
        if not self.session:
            self.connect_to_edx_db()
        query = (
            select(self.User)
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
                )
            )
            .slice(start, stop)
        )
        return self.session.scalars(query).all()

    def get_enrollments_count(self):
        """Get enrollments count from OpenEdxDb"""
        if not self.session:
            self.connect_to_edx_db()
        query_count = select(count(self.StudentCourseEnrollment.id)).join(
            self.CourseOverview,
            self.StudentCourseEnrollment.course_id == self.CourseOverview.id,
        )
        return self.session.execute(query_count).scalar()

    def get_enrollments(self, start, stop):
        """Get enrollments from OpenEdxDb by slicing"""
        if not self.session:
            self.connect_to_edx_db()
        query = (
            select(self.StudentCourseEnrollment, self.User)
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
                joinedload(self.StudentCourseEnrollment.auth_user).load_only(
                    self.User.username,
                ),
            )
            .slice(start, stop)
        )
        return self.session.scalars(query).all()
