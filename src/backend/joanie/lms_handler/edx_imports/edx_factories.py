"""Factory classes for generating fake data for testing."""
import factory
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from joanie.lms_handler.edx_imports import edx_models

engine = create_engine("sqlite://")
session = scoped_session(sessionmaker(bind=engine))


class EdxUniversityFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake OpenEdX universities.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.UniversitiesUniversity
        sqlalchemy_session = session

    code = factory.Faker("pystr")
    name = factory.Faker("company")
    logo = factory.Faker("file_name")


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
    course_id = factory.Sequence(
        lambda n: f"course-v1:edX+{factory.Faker('pystr')}+{n}"
    )
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
