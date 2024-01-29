"""Models for the Open edX database."""
import datetime
import decimal
from typing import List, Optional

from sqlalchemy import DECIMAL, DateTime, Double, ForeignKeyConstraint, Index, String
from sqlalchemy.dialects.mysql import INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models in the database."""


class AuthUser(Base):
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
    is_staff: Mapped[int] = mapped_column(TINYINT(1))
    is_active: Mapped[int] = mapped_column(TINYINT(1))
    is_superuser: Mapped[int] = mapped_column(TINYINT(1))
    date_joined: Mapped[datetime.datetime] = mapped_column(DateTime)
    last_login: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    student_courseenrollment: Mapped[List["StudentCourseenrollment"]] = relationship(
        "StudentCourseenrollment", back_populates="user"
    )


class CourseOverviewsCourseoverview(Base):
    """Model for the `course_overviews_courseoverview` table."""

    __tablename__ = "course_overviews_courseoverview"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    _location: Mapped[str] = mapped_column(String(255))
    display_number_with_default: Mapped[str] = mapped_column(LONGTEXT)
    display_org_with_default: Mapped[str] = mapped_column(LONGTEXT)
    course_image_url: Mapped[str] = mapped_column(LONGTEXT)
    certificates_show_before_end: Mapped[int] = mapped_column(TINYINT(1))
    has_any_active_web_certificate: Mapped[int] = mapped_column(TINYINT(1))
    cert_name_short: Mapped[str] = mapped_column(LONGTEXT)
    cert_name_long: Mapped[str] = mapped_column(LONGTEXT)
    mobile_available: Mapped[int] = mapped_column(TINYINT(1))
    visible_to_staff_only: Mapped[int] = mapped_column(TINYINT(1))
    _pre_requisite_courses_json: Mapped[str] = mapped_column(LONGTEXT)
    cert_html_view_enabled: Mapped[int] = mapped_column(TINYINT(1))
    invitation_only: Mapped[int] = mapped_column(TINYINT(1))
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    modified: Mapped[datetime.datetime] = mapped_column(DateTime)
    version: Mapped[int] = mapped_column(INTEGER(11))
    org: Mapped[str] = mapped_column(LONGTEXT)
    display_name: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    start: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    end: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    advertised_start: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    facebook_url: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    social_sharing_url: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    end_of_course_survey_url: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    certificates_display_behavior: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    lowest_passing_grade: Mapped[Optional[decimal.Decimal]] = mapped_column(
        DECIMAL(5, 2)
    )
    days_early_for_beta: Mapped[Optional[decimal.Decimal]] = mapped_column(
        Double(asdecimal=True)
    )
    enrollment_start: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    enrollment_end: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    enrollment_domain: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    max_student_enrollments_allowed: Mapped[Optional[int]] = mapped_column(INTEGER(11))
    announcement: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    catalog_visibility: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    course_video_url: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    effort: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    short_description: Mapped[Optional[str]] = mapped_column(LONGTEXT)


class UniversitiesUniversity(Base):
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
    description: Mapped[str] = mapped_column(LONGTEXT)
    detail_page_enabled: Mapped[int] = mapped_column(TINYINT(1))
    score: Mapped[int] = mapped_column(INTEGER(10))
    short_name: Mapped[str] = mapped_column(String(255))
    is_obsolete: Mapped[int] = mapped_column(TINYINT(1))
    prevent_auto_update: Mapped[int] = mapped_column(TINYINT(1))
    partnership_level: Mapped[str] = mapped_column(String(255))
    banner: Mapped[Optional[str]] = mapped_column(String(100))
    certificate_logo: Mapped[Optional[str]] = mapped_column(String(100))


class StudentCourseenrollment(Base):
    """Model for the `student_courseenrollment` table."""

    __tablename__ = "student_courseenrollment"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"], ["auth_user.id"], name="user_id_refs_id_45948fcded37bc9d"
        ),
        Index("student_courseenrollment_3216ff68", "created"),
        Index("student_courseenrollment_fbfc09f1", "user_id"),
        Index("student_courseenrollment_ff48d8e5", "course_id"),
        Index(
            "student_courseenrollment_user_id_2d2a572f07dd8e37_uniq",
            "user_id",
            "course_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    user_id: Mapped[int] = mapped_column(INTEGER(11))
    course_id: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[int] = mapped_column(TINYINT(1))
    mode: Mapped[str] = mapped_column(String(100))
    created: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    user: Mapped["AuthUser"] = relationship(
        "AuthUser", back_populates="student_courseenrollment"
    )
