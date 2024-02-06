"""Models for the Open edX database."""
from typing import Optional

from sqlalchemy import Index, String
from sqlalchemy.dialects.mysql import INTEGER, TEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models in the database."""


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
