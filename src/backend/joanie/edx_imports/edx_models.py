"""Models for the Open edX database."""
import datetime
import decimal
from typing import List, Optional

from sqlalchemy import DECIMAL, DateTime, Double, ForeignKeyConstraint, Index, String
from sqlalchemy.dialects.mysql import INTEGER, TEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models in the database."""


class User(Base):
    """Model for the `auth_user` table."""

    __tablename__ = "auth_user"
    __table_args__ = (
        Index("email", "email", unique=True),
        Index("username", "username", unique=True),
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    username: Mapped[str] = mapped_column(String(30))
    first_name: Mapped[str] = mapped_column(String(30))
    last_name: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(254))
    password: Mapped[str] = mapped_column(String(128))
    is_staff: Mapped[int] = mapped_column(INTEGER(1))
    is_active: Mapped[int] = mapped_column(INTEGER(1))
    is_superuser: Mapped[int] = mapped_column(INTEGER(1))
    date_joined: Mapped[datetime.datetime] = mapped_column(DateTime)
    last_login: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    student_courseenrollment: Mapped[List["CourseEnrollment"]] = relationship(
        "CourseEnrollment", back_populates="user"
    )
    auth_userprofile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="user"
    )
    user_api_userpreference: Mapped[List["UserPreference"]] = relationship(
        "UserPreference", back_populates="user"
    )


class UserProfile(Base):
    """Model for the `auth_userprofile` table."""

    __tablename__ = "auth_userprofile"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"], ["auth_user.id"], name="user_id_refs_id_3daaa960628b4c11"
        ),
        Index("auth_userprofile_52094d6e", "name"),
        Index("auth_userprofile_551e365c", "level_of_education"),
        Index("auth_userprofile_8a7ac9ab", "language"),
        Index("auth_userprofile_b54954de", "location"),
        Index("auth_userprofile_d85587", "year_of_birth"),
        Index("auth_userprofile_fca3d292", "gender"),
        Index("user_id", "user_id", unique=True),
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    user_id: Mapped[int] = mapped_column(INTEGER(11))
    name: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(255))
    meta: Mapped[str] = mapped_column(TEXT)
    courseware: Mapped[str] = mapped_column(String(255))
    allow_certificate: Mapped[int] = mapped_column(INTEGER(1))
    gender: Mapped[Optional[str]] = mapped_column(String(6))
    mailing_address: Mapped[Optional[str]] = mapped_column(TEXT)
    year_of_birth: Mapped[Optional[int]] = mapped_column(INTEGER(11))
    level_of_education: Mapped[Optional[str]] = mapped_column(String(6))
    goals: Mapped[Optional[str]] = mapped_column(TEXT)
    country: Mapped[Optional[str]] = mapped_column(String(2))
    city: Mapped[Optional[str]] = mapped_column(TEXT)
    bio: Mapped[Optional[str]] = mapped_column(String(3000))
    profile_image_uploaded_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime
    )

    user: Mapped["User"] = relationship("User", back_populates="auth_userprofile")


class UserPreference(Base):
    """Model for the `user_api_userpreference` table."""

    __tablename__ = "user_api_userpreference"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"], ["auth_user.id"], name="user_id_refs_id_2839c1f4f3473b9e"
        ),
        Index("user_api_userpreference_45544485", "key"),
        Index("user_api_userpreference_fbfc09f1", "user_id"),
        Index(
            "user_api_userpreference_user_id_4e4942d73f760072_uniq",
            "user_id",
            "key",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    user_id: Mapped[int] = mapped_column(INTEGER(11))
    key: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(TEXT)

    user: Mapped["User"] = relationship(
        "User", back_populates="user_api_userpreference"
    )


class CourseOverview(Base):
    """Model for the `course_overviews_courseoverview` table."""

    __tablename__ = "course_overviews_courseoverview"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    _location: Mapped[str] = mapped_column(String(255))
    display_number_with_default: Mapped[str] = mapped_column(TEXT)
    display_org_with_default: Mapped[str] = mapped_column(TEXT)
    course_image_url: Mapped[str] = mapped_column(TEXT)
    certificates_show_before_end: Mapped[int] = mapped_column(INTEGER(1))
    has_any_active_web_certificate: Mapped[int] = mapped_column(INTEGER(1))
    cert_name_short: Mapped[str] = mapped_column(TEXT)
    cert_name_long: Mapped[str] = mapped_column(TEXT)
    mobile_available: Mapped[int] = mapped_column(INTEGER(1))
    visible_to_staff_only: Mapped[int] = mapped_column(INTEGER(1))
    _pre_requisite_courses_json: Mapped[str] = mapped_column(TEXT)
    cert_html_view_enabled: Mapped[int] = mapped_column(INTEGER(1))
    invitation_only: Mapped[int] = mapped_column(INTEGER(1))
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    modified: Mapped[datetime.datetime] = mapped_column(DateTime)
    version: Mapped[int] = mapped_column(INTEGER(11))
    org: Mapped[str] = mapped_column(TEXT)
    display_name: Mapped[Optional[str]] = mapped_column(TEXT)
    start: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    end: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    advertised_start: Mapped[Optional[str]] = mapped_column(TEXT)
    facebook_url: Mapped[Optional[str]] = mapped_column(TEXT)
    social_sharing_url: Mapped[Optional[str]] = mapped_column(TEXT)
    end_of_course_survey_url: Mapped[Optional[str]] = mapped_column(TEXT)
    certificates_display_behavior: Mapped[Optional[str]] = mapped_column(TEXT)
    lowest_passing_grade: Mapped[Optional[decimal.Decimal]] = mapped_column(
        DECIMAL(5, 2)
    )
    days_early_for_beta: Mapped[Optional[decimal.Decimal]] = mapped_column(
        Double(asdecimal=True)
    )
    enrollment_start: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    enrollment_end: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    enrollment_domain: Mapped[Optional[str]] = mapped_column(TEXT)
    max_student_enrollments_allowed: Mapped[Optional[int]] = mapped_column(INTEGER(11))
    announcement: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    catalog_visibility: Mapped[Optional[str]] = mapped_column(TEXT)
    course_video_url: Mapped[Optional[str]] = mapped_column(TEXT)
    effort: Mapped[Optional[str]] = mapped_column(TEXT)
    short_description: Mapped[Optional[str]] = mapped_column(TEXT)

    course: Mapped["Course"] = relationship(
        "Course", back_populates="course_overviews_courseoverview"
    )


class Course(Base):
    """Model for the `courses_course` table."""

    __tablename__ = "courses_course"
    __table_args__ = (
        ForeignKeyConstraint(
            ["key"],
            ["course_overviews_courseoverview.id"],
            name="key_id_refs_id_45948fcded37bc9d",
        ),
        Index("backoffice_course_key_4f82e863a3ea2609_uniq", "key", unique=True),
        Index("courses_course_199461f6", "start_date"),
        Index("courses_course_2a8f42e8", "level"),
        Index("courses_course_2d978633", "show_in_catalog"),
        Index("courses_course_3fa9fe1c", "score"),
        Index("courses_course_43e08e6f", "show_about_page"),
        Index("courses_course_7dabfeb7", "enrollment_end_date"),
        Index("courses_course_8a7ac9ab", "language"),
        Index("courses_course_b246e1cb", "end_date"),
        Index("courses_course_cf5d0e16", "enrollment_start_date"),
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    key: Mapped[str] = mapped_column(String(255))
    level: Mapped[str] = mapped_column(String(255))
    score: Mapped[int] = mapped_column(INTEGER(10))
    is_active: Mapped[int] = mapped_column(INTEGER(1))
    prevent_auto_update: Mapped[int] = mapped_column(INTEGER(1))
    modification_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    title: Mapped[str] = mapped_column(String(255))
    short_description: Mapped[str] = mapped_column(TEXT)
    image_url: Mapped[str] = mapped_column(String(255))
    session_number: Mapped[int] = mapped_column(INTEGER(10))
    university_display_name: Mapped[str] = mapped_column(String(255))
    show_in_catalog: Mapped[int] = mapped_column(INTEGER(1))
    language: Mapped[str] = mapped_column(String(255))
    show_about_page: Mapped[int] = mapped_column(INTEGER(1))
    start_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    thumbnails_info: Mapped[Optional[str]] = mapped_column(TEXT)
    enrollment_start_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    enrollment_end_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    certificate_passing_grade: Mapped[Optional[decimal.Decimal]] = mapped_column(
        Double(asdecimal=True)
    )

    course_overviews_courseoverview: Mapped["CourseOverview"] = relationship(
        "CourseOverview", back_populates="course"
    )
    courses_courseuniversityrelation: Mapped[
        List["CourseUniversityRelation"]
    ] = relationship("CourseUniversityRelation", back_populates="course")


class University(Base):
    """Model for the `universities_university` table."""

    __tablename__ = "universities_university"
    __table_args__ = (
        Index("code", "code", unique=True),
        Index("slug", "slug", unique=True),
        Index("universities_university_28ddafdb", "partnership_level"),
        Index("universities_university_3fa9fe1c", "score"),
        Index("universities_university_52094d6e", "name"),
        Index("universities_university_d7f7fdb2", "is_obsolete"),
        Index("universities_university_eff01f3d", "detail_page_enabled"),
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(255))
    logo: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(TEXT)
    detail_page_enabled: Mapped[int] = mapped_column(INTEGER(1))
    score: Mapped[int] = mapped_column(INTEGER(10))
    short_name: Mapped[str] = mapped_column(String(255))
    is_obsolete: Mapped[int] = mapped_column(INTEGER(1))
    prevent_auto_update: Mapped[int] = mapped_column(INTEGER(1))
    partnership_level: Mapped[str] = mapped_column(String(255))
    banner: Mapped[Optional[str]] = mapped_column(String(100))
    certificate_logo: Mapped[Optional[str]] = mapped_column(String(100))

    courses_courseuniversityrelation: Mapped[
        List["CourseUniversityRelation"]
    ] = relationship("CourseUniversityRelation", back_populates="university")


class CourseUniversityRelation(Base):
    """Model for the `courses_courseuniversityrelation` table."""

    __tablename__ = "courses_courseuniversityrelation"
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id"], ["courses_course.id"], name="course_id_refs_id_a613f49d"
        ),
        ForeignKeyConstraint(
            ["university_id"],
            ["universities_university.id"],
            name="university_id_refs_id_666fe783",
        ),
        Index(
            "courses_courseuniversityrel_university_id_45bb9d52955872eb_uniq",
            "university_id",
            "course_id",
            unique=True,
        ),
        Index("courses_courseuniversityrelation_c45f7136", "order"),
        Index("courses_courseuniversityrelation_ca8dbdfe", "university_id"),
        Index("courses_courseuniversityrelation_ff48d8e5", "course_id"),
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    university_id: Mapped[int] = mapped_column(INTEGER(11))
    course_id: Mapped[int] = mapped_column(INTEGER(11))
    order: Mapped[int] = mapped_column(INTEGER(10))

    course: Mapped["Course"] = relationship(
        "Course", back_populates="courses_courseuniversityrelation"
    )
    university: Mapped["University"] = relationship(
        "University", back_populates="courses_courseuniversityrelation"
    )
