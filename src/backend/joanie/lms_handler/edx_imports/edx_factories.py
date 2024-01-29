"""Factory classes for generating fake data for testing."""
import factory
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import registry, Session

from joanie.lms_handler.edx_imports import edx_models

faker = Faker()
engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
session = Session(engine)
registry().metadata.create_all(engine)


class EdxUniversityFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake OpenEdX universities.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.UniversitiesUniversity
        sqlalchemy_session = session

    id = factory.Faker("pyint")
    name = factory.Faker("company")
    slug = factory.Faker("slug")
    code = factory.Faker("pystr")
    logo = factory.Faker("file_name")
    description = factory.Faker("sentence")
    detail_page_enabled = True
    score = factory.Faker("pyint")
    short_name = factory.Faker("company")
    is_obsolete = False
    prevent_auto_update = False
    partnership_level = factory.Faker("pystr")


class EdxCourseOverviewFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake OpenEdX course overviews.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.CourseOverviewsCourseoverview
        sqlalchemy_session = session

    id = factory.Sequence(lambda n: f"course-v1:edX+{factory.Faker('pystr')}+{n}")
    display_name = factory.Faker("sentence")
    start = factory.Faker("date_time")
    end = factory.Faker("date_time")
    enrollment_start = factory.Faker("date_time")
    enrollment_end = factory.Faker("date_time")
    created = factory.Faker("date_time")


class EdxUserFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake OpenEdX users.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.AuthUser
        sqlalchemy_session = session

    username = factory.Faker("user_name")
    password = factory.Faker("password")
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False
    is_superuser = False
    date_joined = factory.Faker("date_time")
    last_login = factory.Faker("date_time")


class EdxEnrollmentFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake OpenEdX enrollments.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.StudentCourseenrollment
        sqlalchemy_session = session

    user_id = factory.Faker("pyint")
    course_id = factory.Sequence(lambda n: f"course-v1:edX+{faker.pystr()}+{n}")
    created = factory.Faker("date_time")
    is_active = True

    @factory.post_generation
    def auth_user(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.auth_user = extracted
        else:
            self.auth_user = EdxUserFactory.create(id=self.user_id)
